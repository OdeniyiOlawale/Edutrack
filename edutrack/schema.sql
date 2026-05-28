-- EduTrack Database Schema
-- Nigerian Secondary School Performance Manager

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────
-- SCHOOL SETTINGS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO settings VALUES
    ('school_name',    'Hillside Secondary School'),
    ('school_address', '14 Education Road, Ilorin, Kwara State'),
    ('school_phone',   '08012345678'),
    ('school_email',   ''),
    ('current_session','2024/2025'),
    ('current_term',   'First Term');

-- ─────────────────────────────────────────────
-- USERS  (teachers, class teachers, principal)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name     TEXT NOT NULL,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('principal','class_teacher','subject_teacher')),
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- CLASSES
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS classes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,   -- e.g. "JSS 1", "SS 1 Science"
    level      TEXT NOT NULL CHECK(level IN ('JSS','SS')),
    department TEXT,                   -- NULL for JSS; Science/Arts/Commercial for SS
    arm        TEXT DEFAULT 'A'        -- future: A, B, C arms
);

INSERT OR IGNORE INTO classes (name, level, department) VALUES
    ('JSS 1',          'JSS', NULL),
    ('JSS 2',          'JSS', NULL),
    ('JSS 3',          'JSS', NULL),
    ('SS 1 Science',   'SS',  'Science'),
    ('SS 1 Arts',      'SS',  'Arts'),
    ('SS 1 Commercial','SS',  'Commercial'),
    ('SS 2 Science',   'SS',  'Science'),
    ('SS 2 Arts',      'SS',  'Arts'),
    ('SS 2 Commercial','SS',  'Commercial'),
    ('SS 3 Science',   'SS',  'Science'),
    ('SS 3 Arts',      'SS',  'Arts'),
    ('SS 3 Commercial','SS',  'Commercial');

-- ─────────────────────────────────────────────
-- SUBJECTS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO subjects (name) VALUES
    -- JSS subjects
    ('Mathematics'),
    ('English Language'),
    ('Basic Science'),
    ('Social Studies'),
    ('Civic Education'),
    ('Agricultural Science'),
    ('Home Economics'),
    ('Computer Studies'),
    ('French'),
    ('Christian/Islamic Religious Studies'),
    ('Physical & Health Education'),
    ('Fine Arts'),
    ('Music'),
    ('Business Studies'),
    ('Yoruba/Hausa/Igbo Language'),
    -- SS subjects (additional)
    ('Physics'),
    ('Chemistry'),
    ('Biology'),
    ('Further Mathematics'),
    ('Geography'),
    ('Literature in English'),
    ('Government'),
    ('History'),
    ('Economics'),
    ('Commerce'),
    ('Accounting'),
    ('Office Practice'),
    ('Marketing');

-- ─────────────────────────────────────────────
-- CLASS–SUBJECT MAPPING
-- which subjects belong to which class
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS class_subjects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id   INTEGER NOT NULL REFERENCES classes(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    sort_order INTEGER DEFAULT 0,
    UNIQUE(class_id, subject_id)
);

-- JSS 1, 2, 3 share the same 15 subjects
-- We'll insert them via the seed script (app.py init)

-- ─────────────────────────────────────────────
-- STUDENTS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT NOT NULL UNIQUE,   -- e.g. STU-001
    full_name   TEXT NOT NULL,
    gender      TEXT CHECK(gender IN ('Male','Female')),
    date_of_birth DATE,
    class_id    INTEGER NOT NULL REFERENCES classes(id),
    is_active   INTEGER DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- ACADEMIC SESSIONS & TERMS
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,   -- e.g. "2024/2025"
    is_current INTEGER DEFAULT 0
);

INSERT OR IGNORE INTO sessions (name, is_current) VALUES ('2024/2025', 1);

CREATE TABLE IF NOT EXISTS terms (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    name       TEXT NOT NULL CHECK(name IN ('First Term','Second Term','Third Term')),
    is_current INTEGER DEFAULT 0,
    UNIQUE(session_id, name)
);

INSERT OR IGNORE INTO terms (session_id, name, is_current)
    SELECT id, 'First Term',  1 FROM sessions WHERE name = '2024/2025';
INSERT OR IGNORE INTO terms (session_id, name, is_current)
    SELECT id, 'Second Term', 0 FROM sessions WHERE name = '2024/2025';
INSERT OR IGNORE INTO terms (session_id, name, is_current)
    SELECT id, 'Third Term',  0 FROM sessions WHERE name = '2024/2025';

-- ─────────────────────────────────────────────
-- SCORES
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    term_id    INTEGER NOT NULL REFERENCES terms(id),
    ca1        REAL CHECK(ca1 >= 0 AND ca1 <= 20),
    ca2        REAL CHECK(ca2 >= 0 AND ca2 <= 20),
    exam       REAL CHECK(exam >= 0 AND exam <= 60),
    -- computed columns (stored for performance)
    ca_total   REAL GENERATED ALWAYS AS (COALESCE(ca1,0) + COALESCE(ca2,0)) STORED,
    total      REAL GENERATED ALWAYS AS (COALESCE(ca1,0) + COALESCE(ca2,0) + COALESCE(exam,0)) STORED,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, subject_id, term_id)
);

-- ─────────────────────────────────────────────
-- TEACHER–CLASS ASSIGNMENTS
-- which teacher is responsible for which class
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teacher_classes (
    user_id  INTEGER NOT NULL REFERENCES users(id),
    class_id INTEGER NOT NULL REFERENCES classes(id),
    PRIMARY KEY (user_id, class_id)
);

-- ─────────────────────────────────────────────
-- VIEWS  (handy query shortcuts)
-- ─────────────────────────────────────────────

-- Student scores with grade and remark
CREATE VIEW IF NOT EXISTS v_student_scores AS
SELECT
    s.id            AS student_id,
    s.student_id    AS student_code,
    s.full_name,
    s.gender,
    c.name          AS class_name,
    c.level,
    c.department,
    sub.name        AS subject_name,
    t.name          AS term_name,
    ses.name        AS session_name,
    sc.ca1,
    sc.ca2,
    sc.ca_total,
    sc.exam,
    sc.total,
    CASE
        WHEN sc.total >= 70 THEN 'A'
        WHEN sc.total >= 60 THEN 'B'
        WHEN sc.total >= 50 THEN 'C'
        WHEN sc.total >= 40 THEN 'D'
        WHEN sc.total IS NOT NULL THEN 'F'
    END AS grade,
    CASE
        WHEN sc.total >= 70 THEN 'Excellent'
        WHEN sc.total >= 60 THEN 'Good'
        WHEN sc.total >= 50 THEN 'Average'
        WHEN sc.total >= 40 THEN 'Below Average'
        WHEN sc.total IS NOT NULL THEN 'Fail'
    END AS remark
FROM students s
JOIN classes   c   ON s.class_id   = c.id
JOIN scores    sc  ON sc.student_id = s.id
JOIN subjects  sub ON sc.subject_id = sub.id
JOIN terms     t   ON sc.term_id    = t.id
JOIN sessions  ses ON t.session_id  = ses.id;

-- Class averages per term
CREATE VIEW IF NOT EXISTS v_class_summary AS
SELECT
    c.id            AS class_id,
    c.name          AS class_name,
    c.level,
    c.department,
    t.id            AS term_id,
    t.name          AS term_name,
    ses.name        AS session_name,
    COUNT(DISTINCT s.id)                    AS total_students,
    ROUND(AVG(sub_avg.avg_score), 1)        AS class_average,
    ROUND(MAX(sub_avg.avg_score), 1)        AS highest_avg,
    ROUND(MIN(sub_avg.avg_score), 1)        AS lowest_avg,
    ROUND(
        100.0 * SUM(CASE WHEN sub_avg.avg_score >= 40 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(DISTINCT s.id), 0), 1
    ) AS pass_rate
FROM classes c
JOIN students s ON s.class_id = c.id AND s.is_active = 1
JOIN terms t
JOIN sessions ses ON t.session_id = ses.id
LEFT JOIN (
    SELECT sc.student_id, sc.term_id,
           ROUND(AVG(sc.total), 1) AS avg_score
    FROM scores sc
    GROUP BY sc.student_id, sc.term_id
) sub_avg ON sub_avg.student_id = s.id AND sub_avg.term_id = t.id
GROUP BY c.id, t.id;
