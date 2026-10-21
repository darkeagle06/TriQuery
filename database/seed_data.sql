-- ============================================================================
-- TriQuery: Seed Dataset (Hackathon Winners, Colleges, Projects, Vector Corpus)
-- ============================================================================

USE triquery_db;

-- 1. Insert Colleges
INSERT INTO colleges (college_id, name, city, state, country, established_year) VALUES
(1, 'IIT Delhi', 'New Delhi', 'Delhi', 'India', 1961),
(2, 'BITS Pilani', 'Pilani', 'Rajasthan', 'India', 1964),
(3, 'IIIT Hyderabad', 'Hyderabad', 'Telangana', 'India', 1998),
(4, 'NIT Trichy', 'Tiruchirappalli', 'Tamil Nadu', 'India', 1964),
(5, 'RV College of Engineering', 'Bengaluru', 'Karnataka', 'India', 1963)
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 2. Insert Hackathons
INSERT INTO hackathons (hackathon_id, name, edition_year, organizer, city, theme, total_prize_pool) VALUES
(1, 'Smart India Hackathon', 2024, 'Ministry of Education', 'New Delhi', 'National Digital Infrastructure', 2500000.00),
(2, 'HackAI Global Summit', 2025, 'AI Open Initiative', 'Bengaluru', 'Artificial Intelligence & Robotics', 1500000.00),
(3, 'DevSprint National', 2025, 'National Tech Council', 'Hyderabad', 'FinTech & Web3 Systems', 1000000.00)
ON DUPLICATE KEY UPDATE name=VALUES(name);

-- 3. Insert Teams
INSERT INTO teams (team_id, team_name, college_id) VALUES
(1, 'NeuralVanguard', 1),   -- IIT Delhi
(2, 'QuantumLeap', 2),      -- BITS Pilani
(3, 'VisionaryX', 3),       -- IIIT Hyderabad
(4, 'CyberKnights', 4),     -- NIT Trichy
(5, 'ByteWave', 5),         -- RVCE
(6, 'DeepPulse', 3)         -- IIIT Hyderabad
ON DUPLICATE KEY UPDATE team_name=VALUES(team_name);

-- 4. Insert Participants
INSERT INTO participants (participant_id, full_name, email, college_id, graduation_year) VALUES
(1, 'Aarav Sharma', 'aarav.sharma@iitd.ac.in', 1, 2026),
(2, 'Diya Patel', 'diya.patel@iitd.ac.in', 1, 2026),
(3, 'Rohan Verma', 'rohan.verma@pilani.bits-pilani.ac.in', 2, 2025),
(4, 'Ananya Iyer', 'ananya.iyer@pilani.bits-pilani.ac.in', 2, 2025),
(5, 'Kabir Mehta', 'kabir.mehta@research.iiit.ac.in', 3, 2026),
(6, 'Meera Reddy', 'meera.reddy@research.iiit.ac.in', 3, 2027),
(7, 'Vikram Chandran', 'vikram.c@nitt.edu', 4, 2025),
(8, 'Pooja Nair', 'pooja.nair@nitt.edu', 4, 2026),
(9, 'Siddharth Rao', 'siddharth.rao@rvce.edu.in', 5, 2026),
(10, 'Tanvi Kulkarni', 'tanvi.k@rvce.edu.in', 5, 2025),
(11, 'Arjun Gupta', 'arjun.gupta@research.iiit.ac.in', 3, 2026),
(12, 'Sana Fatima', 'sana.fatima@research.iiit.ac.in', 3, 2027)
ON DUPLICATE KEY UPDATE full_name=VALUES(full_name);

-- 5. Insert Team Members
INSERT INTO team_members (team_id, participant_id, role) VALUES
(1, 1, 'ML Lead'),
(1, 2, 'Systems Engineer'),
(2, 3, 'Cryptography Specialist'),
(2, 4, 'Full-Stack Developer'),
(3, 5, 'Computer Vision Researcher'),
(3, 6, 'Robotics Engineer'),
(4, 4, 'Guest Contributor'), -- Cross-college collaborator demo
(4, 7, 'Backend Lead'),
(4, 8, 'Security Architect'),
(5, 9, 'Firmware Developer'),
(5, 10, 'Data Analyst'),
(6, 11, 'NLP Researcher'),
(6, 12, 'Pipeline Engineer')
ON DUPLICATE KEY UPDATE role=VALUES(role);

-- 6. Insert Projects (Rich descriptions for Vector Search)
INSERT INTO projects (project_id, team_id, hackathon_id, title, track, short_summary, description, tech_stack, github_url) VALUES
(1, 1, 2, 'AeroVision Autonomous Drone Pathfinder', 'Robotics & AI',
 'Autonomous visual SLAM and pathfinding for UAVs in GPS-denied disaster environments.',
 'AeroVision enables unmanned aerial vehicles to navigate complex indoor and subterranean disaster zones without satellite GPS signals. Using lightweight stereo-vision cameras, real-time depth estimation, and probabilistic occupancy grids, the system autonomously maps obstacle trajectories and dynamically re-routes flight paths in under 15 milliseconds. Features multi-sensor Kalman filtering and edge neural net object avoidance.',
 'Python, C++, PyTorch, ROS2, OpenCV', 'https://github.com/neuralvanguard/aerovision'),

(2, 2, 3, 'VeriMed Zero-Knowledge Health Vault', 'Healthcare & Web3',
 'Privacy-preserving electronic health record verification using zk-SNARKs on distributed ledgers.',
 'VeriMed revolutionizes patient medical confidentiality by permitting hospitals and insurance carriers to cryptographically prove medical claim eligibility without revealing diagnoses or patient identity. Built on succinct non-interactive zero-knowledge arguments of knowledge (zk-SNARKs), the platform guarantees zero leakage of PHI (Protected Health Information) while maintaining tamper-proof audit trails for cross-border insurance settlement.',
 'Rust, Solidity, Circom, Next.js, MySQL', 'https://github.com/quantumleap/verimed'),

(3, 3, 2, 'RadAssist Multi-Modal Chest Radiogram AI', 'Healthcare & AI',
 'Deep learning diagnostic assistant for pulmonary pathology detection from chest X-rays.',
 'RadAssist utilizes vision-language foundation models fine-tuned on clinical chest radiographs to detect 14 distinct thoracic conditions including pneumonia, pneumothorax, and pulmonary nodules. The system produces localized saliency heatmaps with Grad-CAM and generates explainable diagnostic summaries with structured differential diagnosis likelihood scores for attending radiologists.',
 'Python, PyTorch, TorchVision, FastAPI, Docker', 'https://github.com/visionaryx/radassist'),

(4, 4, 3, 'SentinelStream Real-Time Fraud Shield', 'FinTech & Security',
 'Sub-millisecond credit card anomaly detection using streaming graph neural networks.',
 'SentinelStream intercepts banking transaction pipelines via Apache Kafka to evaluate credit card fraud probability under strict 5-millisecond latency budgets. By transforming cardholder-merchant interaction graphs into dynamic temporal graph embeddings, it catches sophisticated synthetic identity rings and bust-out credit card fraud patterns that evade legacy rule-based scoring engines.',
 'Python, PyTorch Geometric, Apache Kafka, Redis, MySQL', 'https://github.com/cyberknights/sentinelstream'),

(5, 5, 1, 'VoltSync Decentralized Smart Grid Balancer', 'Clean Energy & IoT',
 'Peer-to-peer microgrid load balancing with embedded IoT power metering.',
 'VoltSync manages decentralized renewable energy exchange across local community microgrids. Using smart sensors installed on solar photovoltaic panels and battery storage banks, local power nodes dynamically bid and settle excess electricity supply using an automated market maker algorithm, mitigating grid frequency instability and peak-hour blackouts.',
 'C++, Embedded C, ESP32, Python, MQTT, TimescaleDB', 'https://github.com/bytewave/voltsync'),

(6, 6, 2, 'KaggleMind Autonomous Data Science Agent', 'Developer Tools & AI',
 'Autonomous agentic workflow for automated feature engineering and tabular model tuning.',
 'KaggleMind orchestrates automated end-to-end data science pipelines for high-dimensional tabular datasets. It executes automated exploratory data analysis, cleans missing and anomalous signals, generates mathematical polynomial and interaction features, performs Bayesian hyperparameter optimization, and outputs production-ready Scikit-Learn pipelines accompanied by full model explainability reports.',
 'Python, Scikit-Learn, LightGBM, Optuna, FastAPI', 'https://github.com/deeppulse/kagglemind')
ON DUPLICATE KEY UPDATE title=VALUES(title);

-- 7. Insert Awards
INSERT INTO awards (award_id, project_id, hackathon_id, prize_category, rank_position, cash_prize) VALUES
(1, 1, 2, '1st Place Grand Winner', 1, 500000.00),
(2, 3, 2, 'Best Healthcare AI Innovation', 2, 250000.00),
(3, 2, 3, 'Best Cryptographic Security Project', 1, 350000.00),
(4, 4, 3, 'FinTech Runner Up', 2, 150000.00),
(5, 5, 1, 'National Clean Energy Excellence', 1, 500000.00),
(6, 6, 2, 'Best AI Developer Tool', 3, 100000.00)
ON DUPLICATE KEY UPDATE prize_category=VALUES(prize_category);
