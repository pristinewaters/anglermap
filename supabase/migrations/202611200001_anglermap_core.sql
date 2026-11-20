-- AnglerMap account and multi-tenant foundation
-- Apply in Supabase SQL Editor or with Supabase CLI migrations.
-- Never expose the service_role key in the browser.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  email text,
  preferences jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('angler','operator','territory_admin')),
  status text not null default 'active' check (status in ('active','pending','suspended')),
  created_at timestamptz not null default now(),
  primary key (user_id, role)
);

create table if not exists public.territories (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id),
  name text not null,
  region text not null default 'Magallanes',
  status text not null default 'draft' check (status in ('draft','published','paused','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.territory_memberships (
  territory_id uuid not null references public.territories(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('owner','administrator','staff','guide')),
  created_at timestamptz not null default now(),
  primary key (territory_id, user_id)
);

create table if not exists public.territory_sectors (
  id uuid primary key default gen_random_uuid(),
  territory_id uuid not null references public.territories(id) on delete cascade,
  waterbody_ref text,
  name text not null,
  capacity_per_day integer not null default 4 check (capacity_per_day > 0),
  daily_price_clp integer not null default 0 check (daily_price_clp >= 0),
  status text not null default 'draft' check (status in ('draft','open','closed')),
  geometry jsonb,
  access_instructions text,
  exit_instructions text,
  rules jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.operator_agreements (
  id uuid primary key default gen_random_uuid(),
  territory_id uuid not null references public.territories(id) on delete cascade,
  operator_user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'pending' check (status in ('pending','active','paused','ended')),
  commission_percent numeric(5,2) check (commission_percent between 0 and 100),
  terms jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (territory_id, operator_user_id)
);

create table if not exists public.bookings (
  id uuid primary key default gen_random_uuid(),
  sector_id uuid not null references public.territory_sectors(id),
  user_id uuid not null references auth.users(id),
  operator_agreement_id uuid references public.operator_agreements(id),
  fishing_date date not null,
  angler_count integer not null check (angler_count > 0),
  status text not null default 'requested' check (status in ('requested','approved_pending_payment','confirmed','rejected','cancelled','expired')),
  total_price_clp integer not null default 0 check (total_price_clp >= 0),
  payment_reference text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.access_events (
  id uuid primary key default gen_random_uuid(),
  booking_id uuid not null references public.bookings(id) on delete cascade,
  event_type text not null check (event_type in ('check_in','check_out','incident')),
  recorded_by uuid references auth.users(id),
  notes text,
  recorded_at timestamptz not null default now()
);

create index if not exists territory_memberships_user_idx on public.territory_memberships(user_id);
create index if not exists territory_sectors_territory_idx on public.territory_sectors(territory_id);
create index if not exists bookings_sector_date_idx on public.bookings(sector_id, fishing_date);
create index if not exists bookings_user_idx on public.bookings(user_id);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (user_id, display_name, email)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'name',''), new.email)
  on conflict (user_id) do update set email = excluded.email;
  insert into public.user_roles (user_id, role, status)
  values (new.id, 'angler', 'active')
  on conflict (user_id, role) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create or replace function public.add_territory_owner_membership()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.territory_memberships (territory_id, user_id, role)
  values (new.id, new.owner_user_id, 'owner')
  on conflict (territory_id, user_id) do nothing;
  insert into public.user_roles (user_id, role, status)
  values (new.owner_user_id, 'territory_admin', 'active')
  on conflict (user_id, role) do nothing;
  return new;
end;
$$;

drop trigger if exists on_territory_created on public.territories;
create trigger on_territory_created
  after insert on public.territories
  for each row execute procedure public.add_territory_owner_membership();

alter table public.profiles enable row level security;
alter table public.user_roles enable row level security;
alter table public.territories enable row level security;
alter table public.territory_memberships enable row level security;
alter table public.territory_sectors enable row level security;
alter table public.operator_agreements enable row level security;
alter table public.bookings enable row level security;
alter table public.access_events enable row level security;

drop policy if exists "profile owner reads and updates" on public.profiles;
create policy "profile owner reads and updates" on public.profiles
  for all to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

drop policy if exists "users read own roles" on public.user_roles;
create policy "users read own roles" on public.user_roles
  for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "territories visible to public or members" on public.territories;
create policy "territories visible to public or members" on public.territories
  for select to anon, authenticated using (
    status = 'published' or owner_user_id = (select auth.uid()) or
    exists (select 1 from public.territory_memberships m
      where m.territory_id = id and m.user_id = (select auth.uid()))
  );

drop policy if exists "owners create territories" on public.territories;
create policy "owners create territories" on public.territories
  for insert to authenticated with check (owner_user_id = (select auth.uid()));

drop policy if exists "territory owners update" on public.territories;
create policy "territory owners update" on public.territories
  for update to authenticated using (owner_user_id = (select auth.uid()))
  with check (owner_user_id = (select auth.uid()));

drop policy if exists "members read memberships" on public.territory_memberships;
-- A user can read their own membership rows. Team-wide administration
-- is intentionally reserved for a trusted server-side endpoint to avoid
-- recursive RLS policy evaluation between territories and memberships.
create policy "users read own memberships" on public.territory_memberships
  for select to authenticated using (user_id = (select auth.uid()));

drop policy if exists "sector read access" on public.territory_sectors;
create policy "sector read access" on public.territory_sectors
  for select to anon, authenticated using (
    exists (select 1 from public.territories t
      where t.id = territory_id and t.status = 'published')
    or exists (select 1 from public.territory_memberships m
      where m.territory_id = territory_id and m.user_id = (select auth.uid()))
  );

drop policy if exists "territory managers manage sectors" on public.territory_sectors;
create policy "territory managers manage sectors" on public.territory_sectors
  for all to authenticated using (
    exists (select 1 from public.territory_memberships m
      where m.territory_id = territory_id and m.user_id = (select auth.uid())
      and m.role in ('owner','administrator'))
  ) with check (
    exists (select 1 from public.territory_memberships m
      where m.territory_id = territory_id and m.user_id = (select auth.uid())
      and m.role in ('owner','administrator'))
  );

drop policy if exists "agreement visible to parties" on public.operator_agreements;
create policy "agreement visible to parties" on public.operator_agreements
  for select to authenticated using (
    operator_user_id = (select auth.uid()) or exists (
      select 1 from public.territories t
      where t.id = territory_id and t.owner_user_id = (select auth.uid())
    )
  );

drop policy if exists "booking visible to angler or territory team" on public.bookings;
create policy "booking visible to angler or territory team" on public.bookings
  for select to authenticated using (
    user_id = (select auth.uid()) or exists (
      select 1 from public.territory_sectors s
      join public.territory_memberships m on m.territory_id = s.territory_id
      where s.id = sector_id and m.user_id = (select auth.uid())
    )
  );

drop policy if exists "angler creates own booking request" on public.bookings;
create policy "angler creates own booking request" on public.bookings
  for insert to authenticated with check (
    user_id = (select auth.uid()) and status = 'requested'
    and exists (
      select 1 from public.territory_sectors s
      join public.territories t on t.id = s.territory_id
      where s.id = sector_id and s.status = 'open' and t.status = 'published'
    )
  );

drop policy if exists "access events visible to booking parties" on public.access_events;
create policy "access events visible to booking parties" on public.access_events
  for select to authenticated using (
    exists (select 1 from public.bookings b
      where b.id = booking_id and (
        b.user_id = (select auth.uid()) or exists (
          select 1 from public.territory_sectors s
          join public.territory_memberships m on m.territory_id = s.territory_id
          where s.id = b.sector_id and m.user_id = (select auth.uid())
        )
      ))
  );

-- Deliberately no client-side policies for assigning privileged roles,
-- managing memberships, confirming payment, or changing booking status.
-- Those actions must be implemented by trusted server-side functions.
