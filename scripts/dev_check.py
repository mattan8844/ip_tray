#!/usr/bin/env python3
"""
Quick developer check to verify imports and core functions without launching GUI.
"""
import argparse

from ip_tray.net import (
    get_public_ip_and_country,
    get_local_ip,
    get_network_speeds,
    get_traffic_totals,
    human_speed,
    human_traffic_gb,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Quick non-GUI sanity checks")
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip checks that rely on external network requests",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.skip_network:
        print("Checking public IP and country...")
        ip, cc = get_public_ip_and_country()
        print("Public IP:", ip, "Country:", cc)
    else:
        print("Skipping public IP check (--skip-network)")

    print("Local IP:", get_local_ip())

    print("Measuring speeds for 1s...")
    down, up = get_network_speeds(interval=1.0)
    print("Down:", human_speed(down), "Up:", human_speed(up))

    dtotal, utotal = get_traffic_totals()
    print("Totals:", "↓", human_traffic_gb(dtotal), "↑", human_traffic_gb(utotal))


if __name__ == "__main__":
    main()
