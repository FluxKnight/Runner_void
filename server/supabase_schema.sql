-- VOID RUNNER Supabase database schema
-- Supabase Dashboard -> SQL Editor -> New query -> paste this -> Run

create table if not exists public.void_runner_users (
  username text primary key,
  password_hash text not null,
  profile jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.void_runner_set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_void_runner_users_updated_at on public.void_runner_users;
create trigger trg_void_runner_users_updated_at
before update on public.void_runner_users
for each row execute function public.void_runner_set_updated_at();

-- Indexes for future leaderboard / admin tools.
create index if not exists idx_void_runner_users_updated_at on public.void_runner_users (updated_at desc);
create index if not exists idx_void_runner_users_profile_best_score on public.void_runner_users (((profile->>'best_score')::int));
create index if not exists idx_void_runner_users_profile_best_level on public.void_runner_users (((profile->>'best_level')::int));
create index if not exists idx_void_runner_users_profile_best_gems on public.void_runner_users (((profile->>'best_gems')::int));
