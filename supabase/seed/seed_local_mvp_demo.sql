-- ==========================================================================
-- Seed: Local MVP Demo Data
-- Gate 51 — Supabase Schema Design
-- Run after migration 000001 and 000002.
-- Uses fixed UUIDs so re-running is idempotent (insert ... on conflict do nothing).
-- ==========================================================================

-- --------------------------------------------------------------------------
-- Organization
-- --------------------------------------------------------------------------
insert into organizations (id, name, slug, type)
values (
  '00000000-0000-0000-0000-000000000001',
  'Quanta Aptus Local Demo',
  'quanta-aptus-local-demo',
  'platform'
)
on conflict (id) do nothing;

-- --------------------------------------------------------------------------
-- Subjects — full adapter registry (22 subjects)
-- --------------------------------------------------------------------------
insert into subjects
  (id, board, level, subject_slug, subject_name, syllabus_code, adapter_name, adapter_status, adapter_version, is_active)
values
  -- Science (full + basic)
  ('10000000-0000-0000-0000-000000000001', 'cambridge', 'igcse', 'physics_0625',                 'Physics',                    '0625', 'PhysicsAdapter',               'full_adapter',  'v1', true),
  ('10000000-0000-0000-0000-000000000002', 'cambridge', 'igcse', 'chemistry_0620',               'Chemistry',                  '0620', 'ChemistryAdapter',             'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000003', 'cambridge', 'igcse', 'biology_0610',                 'Biology',                    '0610', 'BiologyAdapter',               'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000004', 'cambridge', 'igcse', 'combined_science_0653',        'Combined Science',           '0653', 'CombinedScienceAdapter',       'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000005', 'cambridge', 'igcse', 'co_ordinated_sciences_0654',   'Co-ordinated Sciences',      '0654', 'CombinedScienceAdapter',       'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000006', 'cambridge', 'igcse', 'environmental_management_0680','Environmental Management',   '0680', 'EnvironmentalManagementAdapter','basic_adapter', 'v1', true),
  -- Mathematics
  ('10000000-0000-0000-0000-000000000007', 'cambridge', 'igcse', 'mathematics_0580',             'Mathematics',                '0580', 'MathematicsAdapter',           'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000008', 'cambridge', 'igcse', 'additional_mathematics_0606',  'Additional Mathematics',     '0606', 'AdditionalMathematicsAdapter', 'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000009', 'cambridge', 'igcse', 'international_mathematics_0607','International Mathematics', '0607', 'InternationalMathematicsAdapter','basic_adapter','v1', true),
  -- Computer Science / ICT
  ('10000000-0000-0000-0000-000000000010', 'cambridge', 'igcse', 'computer_science_0478',        'Computer Science',           '0478', 'ComputerScienceAdapter',       'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000011', 'cambridge', 'igcse', 'ict_0417',                     'Information and Communication Technology', '0417', 'ICTAdapter', 'basic_adapter', 'v1', true),
  -- Business / Humanities
  ('10000000-0000-0000-0000-000000000012', 'cambridge', 'igcse', 'business_studies_0450',        'Business Studies',           '0450', 'BusinessAdapter',              'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000013', 'cambridge', 'igcse', 'economics_0455',               'Economics',                  '0455', 'EconomicsAdapter',             'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000014', 'cambridge', 'igcse', 'accounting_0452',              'Accounting',                 '0452', 'AccountingAdapter',            'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000015', 'cambridge', 'igcse', 'geography_0460',               'Geography',                  '0460', 'GeographyAdapter',             'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000016', 'cambridge', 'igcse', 'history_0470',                 'History',                    '0470', 'HistoryAdapter',               'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000017', 'cambridge', 'igcse', 'global_perspectives_0457',     'Global Perspectives',        '0457', 'GlobalPerspectivesAdapter',    'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000018', 'cambridge', 'igcse', 'sociology_0495',               'Sociology',                  '0495', 'SociologyAdapter',             'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000019', 'cambridge', 'igcse', 'travel_and_tourism_0471',      'Travel and Tourism',         '0471', 'TravelTourismAdapter',         'basic_adapter', 'v1', true),
  -- Languages
  ('10000000-0000-0000-0000-000000000020', 'cambridge', 'igcse', 'english_first_language_0500',  'English - First Language',   '0500', 'EnglishLanguageAdapter',       'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000021', 'cambridge', 'igcse', 'english_second_language_0510', 'English - Second Language',  '0510', 'EnglishLanguageAdapter',       'basic_adapter', 'v1', true),
  ('10000000-0000-0000-0000-000000000022', 'cambridge', 'igcse', 'english_literature_0475',      'English Literature',         '0475', 'LiteratureAdapter',            'basic_adapter', 'v1', true)
on conflict (subject_slug) do nothing;

-- --------------------------------------------------------------------------
-- Demo student (no auth.uid() in seed; profile_id left null for local demo)
-- --------------------------------------------------------------------------
insert into students (id, organization_id, profile_id, display_name, external_code, status)
values (
  '20000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001',
  null,
  'Local Demo Student',
  'local_demo_student',
  'active'
)
on conflict (id) do nothing;

-- --------------------------------------------------------------------------
-- Demo resource package: Physics 0625 v2
-- Reflects the active publish package from Local MVP v1.
-- --------------------------------------------------------------------------
insert into resource_packages
  (id, subject_id, package_key, version, title, status,
   resource_count, student_resource_count, teacher_resource_count,
   published_at)
values (
  '30000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  'cambridge_igcse_physics_0625_resource_package_v2',
  2,
  'Cambridge IGCSE Physics 0625 — Resource Package v2',
  'active',
  27,
  23,
  27,
  now()
)
on conflict (package_key) do nothing;
