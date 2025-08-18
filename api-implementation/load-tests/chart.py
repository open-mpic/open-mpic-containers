#!/usr/bin/env python3
import json
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import sys
import os
import argparse


def main():
    parser = argparse.ArgumentParser(description="Plot Vegeta latency time-series from results.jsonl")
    parser.add_argument("--testdir", required=True, help="Path to the test directory (e.g., load-tests/dcv-http-01)")
    parser.add_argument("--title", default="Vegeta Plot", help="Plot title (optional)")
    args = parser.parse_args()

    test_dir = args.testdir
    plot_title = args.title
    output_dir = os.path.join(test_dir, "output")
    results_path = os.path.join(output_dir, "results.jsonl")
    plot_path = os.path.join(output_dir, "latency-timeseries-plot.png")

    # Group data by status code
    code_to_times = {}
    code_to_latencies = {}
    all_timestamps = []
    with open(results_path) as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                if "timestamp" in entry and "latency" in entry and "code" in entry:
                    t = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
                    all_timestamps.append(t)
                    code = str(entry["code"])
                    code_to_times.setdefault(code, []).append(t)
                    code_to_latencies.setdefault(code, []).append(entry["latency"] / 1_000_000)

    if not all_timestamps:
        raise ValueError(f"No data found in {results_path}. Ensure vegeta encode was used.")

    start_time = all_timestamps[0]
    plt.figure(figsize=(10, 6))
    colors = ["blue", "green", "gold", "orange", "black", "purple", "red"]
    for idx, (code, times) in enumerate(code_to_times.items()):
        elapsed_sec = [(t - start_time).total_seconds() for t in times]
        latencies = code_to_latencies[code]
        color = colors[idx % len(colors)]
        count = len(times)
        label = f"{code} ({count})"
        if count == 1:
            plt.scatter(elapsed_sec, latencies, color=color, s=40, label=label, zorder=3)
        else:
            plt.plot(elapsed_sec, latencies, color=color, alpha=0.7, label=label)

    plt.title(plot_title)
    plt.xlabel("Seconds elapsed")
    plt.ylabel("Latency (ms)")
    plt.legend(title="Status Code")
    plt.grid(True)
    plt.savefig(plot_path)
    print(f"Plot saved as {plot_path}")


if __name__ == "__main__":
    main()
