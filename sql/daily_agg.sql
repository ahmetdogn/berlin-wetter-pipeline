delete from mart.weather_daily where day = '{{ ds }}';

insert into mart.weather_daily
select
    station_id,
    ts::date,
    min(temperature),
    max(temperature),
    round(avg(temperature)::numeric, 2),
    round(sum(precipitation)::numeric, 1),
    max(wind_speed),
    count(*)
from raw.weather_hourly
where ts::date = '{{ ds }}'
group by station_id, ts::date;
