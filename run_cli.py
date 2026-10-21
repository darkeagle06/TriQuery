#!/usr/bin/env python
"""
TriQuery Multi-Paradigm CLI Entry Point.
Unifies Relational (MySQL/SQLite), Graph (NetworkX), and Vector (Cosine/Embeddings).

Usage:
    python run_cli.py                                      # Launch interactive menu
    python run_cli.py status                               # Relational table status
    python run_cli.py projects                             # 5-way relational JOIN
    python run_cli.py graph-status                         # Graph entity/topology status
    python run_cli.py graph-team "NeuralVanguard"          # 1-hop team membership traversal
    python run_cli.py graph-path -s "participant:1" -t "participant:5"  # Shortest path
    python run_cli.py vector-status                        # Vector index health and metadata
    python run_cli.py vector-search "AI solutions for traffic congestion"
    python run_cli.py vector-search "Secure digital identity platforms"
    python run_cli.py vector-explain "AI solutions for traffic congestion"
    python run_cli.py unified-presets                      # List multi-paradigm query benchmarks
    python run_cli.py unified-query 1                      # Relational-only benchmark query
    python run_cli.py unified-query 4                      # 2-engine hybrid (SQL + Vector)
    python run_cli.py unified-query 5                      # 3-way multi-paradigm query
    python run_cli.py unified-explain 5                    # Explain execution plan & RRF ranking
"""

import sys
from src.cli.main import main

if __name__ == "__main__":
    main()
