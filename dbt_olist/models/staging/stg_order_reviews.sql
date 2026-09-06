with source as (
    select * from {{ source('silver', 'order_reviews') }}
),

renamed as (
    select
        review_id,
        order_id,
        review_score,
        review_comment_title,
        review_comment_message,
        review_creation_date,
        review_answer_timestamp,
        case when has_review_comment = 1 then true else false end as has_review_comment
    from source
)

select * from renamed
