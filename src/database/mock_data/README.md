# database/mock_data/

`sample_data.sql` — seed data loaded by `../scripts/init_db.py`: 4 regions,
8 products, 10 customers, 70 sales rows across Jan-Jun 2024. Laptop volume
is deliberately weighted toward the Asia customers to mirror the "Laptop
dominates Asia revenue" example in
`docs/01_business_requirements.md > Example Conversation`.

Assumes a freshly recreated schema (IDs start at 1) — always run after
`schema.sql`, not standalone.
