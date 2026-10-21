-- ============================================================================
-- TriQuery: Multi-Paradigm Query Engine
-- Relational Schema: Hackathon Benchmark & Demonstration Dataset
-- Target RDBMS: MySQL 8.x
-- Engine: InnoDB (Full ACID compliance, Foreign Key enforcement, Row-Level Locking)
-- Normalization: Third Normal Form (3NF)
-- ============================================================================

-- Create database if not exists (User can override via .env)
CREATE DATABASE IF NOT EXISTS triquery_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE triquery_db;

-- ----------------------------------------------------------------------------
-- Table: colleges
-- Represents academic institutions affiliated with participants and teams.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS colleges (
    college_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    established_year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_college_name UNIQUE (name),
    INDEX idx_colleges_location (state, city)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Table: hackathons
-- Represents hackathon events, hosting organizations, and focus themes.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hackathons (
    hackathon_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    edition_year INT NOT NULL,
    organizer VARCHAR(150) NOT NULL,
    city VARCHAR(100) NOT NULL,
    theme VARCHAR(100) NOT NULL,
    total_prize_pool DECIMAL(12, 2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hackathon_name_year UNIQUE (name, edition_year),
    INDEX idx_hackathons_year (edition_year),
    INDEX idx_hackathons_theme (theme)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Table: teams
-- Represents student/builder teams representing a primary institution.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    team_name VARCHAR(150) NOT NULL,
    college_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_teams_college FOREIGN KEY (college_id)
        REFERENCES colleges (college_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT uk_team_per_college UNIQUE (team_name, college_id),
    INDEX idx_teams_college (college_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Table: participants
-- Represents individual student developers, designers, and researchers.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS participants (
    participant_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) NOT NULL,
    college_id INT NOT NULL,
    graduation_year INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_participant_email UNIQUE (email),
    CONSTRAINT fk_participants_college FOREIGN KEY (college_id)
        REFERENCES colleges (college_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_participants_college (college_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Table: team_members
-- Junction table mapping many-to-many relationship between teams and participants.
-- Natural bridge for Graph Engine edge construction: (:Participant)-[:MEMBER_OF]->(:Team)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS team_members (
    team_id INT NOT NULL,
    participant_id INT NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'Developer',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_id, participant_id),
    CONSTRAINT fk_tm_team FOREIGN KEY (team_id)
        REFERENCES teams (team_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_tm_participant FOREIGN KEY (participant_id)
        REFERENCES participants (participant_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    INDEX idx_tm_participant (participant_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Table: projects
-- Represents projects built and submitted by teams at a specific hackathon.
-- Description and summary columns serve as the primary corpus for Vector Search.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    hackathon_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    track VARCHAR(100) NOT NULL,
    short_summary VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    tech_stack VARCHAR(255) NOT NULL,
    github_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_team_hackathon_project UNIQUE (team_id, hackathon_id),
    CONSTRAINT fk_projects_team FOREIGN KEY (team_id)
        REFERENCES teams (team_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_projects_hackathon FOREIGN KEY (hackathon_id)
        REFERENCES hackathons (hackathon_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_projects_track (track),
    INDEX idx_projects_hackathon (hackathon_id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------------------------
-- Table: awards
-- Represents winning accolades, rank positions, and cash prizes won by projects.
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS awards (
    award_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    hackathon_id INT NOT NULL,
    prize_category VARCHAR(100) NOT NULL,
    rank_position INT NOT NULL,
    cash_prize DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uk_hackathon_project_award UNIQUE (hackathon_id, project_id, prize_category),
    CONSTRAINT fk_awards_project FOREIGN KEY (project_id)
        REFERENCES projects (project_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_awards_hackathon FOREIGN KEY (hackathon_id)
        REFERENCES hackathons (hackathon_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    INDEX idx_awards_rank (rank_position),
    INDEX idx_awards_category (prize_category)
) ENGINE=InnoDB;