create schema if not exists raw;
create schema if not exists mart;

create table if not exists raw.stations (
    station_id  text primary key,
    name        text not null,
    lat         double precision not null,
    lon         double precision not null
);

insert into raw.stations values
    ('tub',     'TU Berlin Charlottenburg', 52.5125, 13.3269),
    ('adlersh', 'Adlershof',                52.4339, 13.5310),
    ('tegel',   'Tegel',                    52.5588, 13.2884),
    ('mitte',   'Alexanderplatz',           52.5219, 13.4132)
on conflict (station_id) do nothing;

create table if not exists raw.weather_hourly (
    station_id      text not null references raw.stations(station_id),
    ts              timestamp not null,
    temperature     real,
    humidity        real,
    precipitation   real,
    wind_speed      real,
    loaded_at       timestamptz not null default now(),
    primary key (station_id, ts)
);

create table if not exists mart.weather_daily (
    station_id      text not null,
    day             date not null,
    temp_min        real,
    temp_max        real,
    temp_avg        real,
    precip_sum      real,
    wind_max        real,
    n_hours         int,
    primary key (station_id, day)
);
