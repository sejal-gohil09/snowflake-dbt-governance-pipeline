{#
  mask_pii macro — Defence-in-depth PII hashing at the dbt transformation layer.
  Hashes a column using SHA-256 before data reaches the marts layer.
  In Snowflake: SHA2(column, 256)
  In Postgres:  encode(digest(column, 'sha256'), 'hex')
#}

{% macro mask_pii(column_name) %}
  {% if target.type == 'snowflake' %}
    SHA2({{ column_name }}, 256)
  {% elif target.type == 'postgres' %}
    encode(digest({{ column_name }}, 'sha256'), 'hex')
  {% else %}
    SHA2({{ column_name }}, 256)
  {% endif %}
{% endmacro %}


{#
  mask_email — Partial masking for display (not full hash).
  Shows first character + domain: j***@gmail.com
#}

{% macro mask_email(column_name) %}
  {% if target.type == 'snowflake' %}
    REGEXP_REPLACE({{ column_name }}, '^([a-zA-Z0-9]).*(@.*)$', '\\1***\\2')
  {% elif target.type == 'postgres' %}
    REGEXP_REPLACE({{ column_name }}, '^([a-zA-Z0-9]).*(@.*)$', '\\1***\\2')
  {% else %}
    REGEXP_REPLACE({{ column_name }}, '^([a-zA-Z0-9]).*(@.*)$', '\\1***\\2')
  {% endif %}
{% endmacro %}


{#
  mask_phone — Masks middle digits of phone numbers: +44 *** *** 7890
#}

{% macro mask_phone(column_name) %}
  {% if target.type == 'snowflake' %}
    REGEXP_REPLACE({{ column_name }}, '(\\+\\d{1,3})\\s+\\d{3,}\\s+\\d{3,}\\s+(\\d{4})', '\\1 *** *** \\2')
  {% else %}
    REGEXP_REPLACE({{ column_name }}, '(\\+\\d{1,3})\\s+\\d{3,}\\s+\\d{3,}\\s+(\\d{4})', '\\1 *** *** \\2')
  {% endif %}
{% endmacro %}
