with source as (
    select * from {{ source('silver', 'geolocation') }}
),

renamed as (
    select
        geolocation_zip_code_prefix as zip_code_prefix,
        geolocation_lat as latitude,
        geolocation_lng as longitude,
        geolocation_city as city,
        geolocation_state as state,
        record_count as raw_point_count
    from source
)

select * from renamed
