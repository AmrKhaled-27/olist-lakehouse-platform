/* ==============================================================================
   MODEL: dim_products
   LAYER: Core Dimension
   AUTHOR: Assistant Reference Model
   ==============================================================================
   DESCRIPTION:
     Product catalog dimension table. Enriches raw products with English
     category translations, calculates 3D physical volume in cm3, and assigns
     weight tier categories.
   ============================================================================== */

with products as (
    select * from {{ ref('stg_products') }}
),

translations as (
    select * from {{ source('silver', 'product_category_name_translation') }}
),

enriched as (
    select
        p.product_id,
        p.product_category_name as category_name_portuguese,
        coalesce(t.product_category_name_english, p.product_category_name, 'unknown') as category_name_english,
        p.product_name_length,
        p.product_description_length,
        p.product_photos_qty,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm,
        -- Calculated 3D volume in cubic centimeters
        round(p.product_length_cm * p.product_height_cm * p.product_width_cm, 2) as product_volume_cm3,
        -- Physical weight tier classification
        case
            when p.product_weight_g is null then 'Unknown'
            when p.product_weight_g < 1000 then 'Light (<1kg)'
            when p.product_weight_g <= 5000 then 'Medium (1-5kg)'
            else 'Heavy (>5kg)'
        end as weight_tier
    from products p
    left join translations t
        on p.product_category_name = t.product_category_name
)

select * from enriched
