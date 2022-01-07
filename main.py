#! /usr/bin/python3.9

"""
Run this code for adding a new peer to your WireGuard server.
Compatible with python3.9+. No third-party library is required, implemented in pure python.
Ensure that you have the necessary permissions and wg, qrencode already installed.
You can use `scp -r ...` for retrieving the config files from your remote
machine to your local computer.
Mahyar@Mahyar24.com, Sat 05 Jun 2021.

"""

import ipaddress
import os
import pathlib
import shutil
import subprocess
import textwrap
from typing import Iterator

# Customize this lines:

ADDRESS = "<URI>:<PORT>"  # Replace placeholders.
DNS = "1.1.1.1"


def check_requirements() -> None:
    """
    This function check if "wg" and "qrencode" is installed or not,
    and if user have superuser access.
    """
    must_installed = {"wg", "qrencode"}
    for program in must_installed:
        assert shutil.which(program) is not None, f"{program!r} must be installed."
    assert os.getuid() == 0, "You must have super user permissions to run this program."


def get_wg_show_output() -> tuple[str, ...]:
    """
    Get information about used ips, interface name, public key and etc.
    By checking output of `wg show` command.
    """
    raw_output = subprocess.check_output(["wg", "show"], text=True)
    raw_list = raw_output.split("\n")
    lines = [
        line.strip() for line in raw_list if line
    ]  # remove emtpy lines and striping.
    assert lines, "Empty output from `wg show` command."
    return tuple(lines)


def find_interface(wg_show_output: tuple[str, ...]) -> str:
    """
    Finding interface name (e.g. wg0).
    """
    for line in wg_show_output:
        if line.startswith("interface: "):
            return line.split()[-1]
    raise Exception("Cannot find interface name.")


def find_server_public_key(wg_show_output: tuple[str, ...]) -> str:
    """
    Finding sever public key. (it's necessary for making new configs).
    """
    for line in wg_show_output:
        if line.startswith("public key: "):
            return line.split()[-1]
    raise Exception("Cannot find server public key")


def get_user() -> str:
    """Get a username for folder and config files name."""
    username = input("Enter Username: ").strip()
    assert username, "Empty username is not allowed."
    return username


def gen_private_key() -> str:
    """Generating private key by running: `wg genkey`. required root access."""
    private_key = subprocess.check_output(["wg", "genkey"], text=True).strip()
    return private_key


def gen_public_key(private_key: str) -> str:
    """Generating public key by running: `echo <private key> | wg pubkey`. required root access."""
    with subprocess.Popen(["echo", private_key], stdout=subprocess.PIPE) as ps_stdout:
        public_key = subprocess.check_output(
            ["wg", "pubkey"], stdin=ps_stdout.stdout, text=True
        ).strip()
        ps_stdout.wait()
    return public_key


def find_address(
    interface_name: str,
) -> tuple[ipaddress.IPv4Network, ipaddress.IPv4Address]:
    """Find ip network by reading config file.
    (e.g. /etc/wireguard/wg0.conf), required root access."""
    assumed_file = pathlib.Path(f"/etc/wireguard/{interface_name}.conf")
    assert assumed_file.is_file(), f"cannot find config file: {assumed_file!r}"
    with open(assumed_file, encoding="utf-8") as config:
        # e.g. if address is 10.10.50.1, it should not use as a peer ip
        # because it makes a collision.
        for line in config.readlines():
            if line.startswith("Address"):
                ip = line.split()[-1]
                return ipaddress.ip_network(ip, strict=False), ipaddress.ip_address(
                    ip.split("/")[0]
                )
    raise Exception("Address not found!")


def find_using_ips(wg_output: tuple[str, ...]) -> Iterator[str]:
    """Find all using ips by reading configs. (e.g. `wg show` output)"""
    for line in wg_output:
        if (
            line.startswith("allowed ips") and "(none)" not in line
        ):  # checking if allowed ips is not (none).
            yield line.split()[-1]


def find_unused_ip(
    used_ips: set[ipaddress.IPv4Address], address: ipaddress.IPv4Network
) -> ipaddress.IPv4Address:
    """We want to find some unused single class A network that are in the subnet of address."""
    for new_ip in address.hosts():
        if new_ip not in used_ips:
            return new_ip
    raise Exception("All valid IPs are used.")


def make_new_ip(interface_name: str, wg_output: tuple[str, ...]) -> str:
    """Returning an unused new valid ip which is in our address network."""
    address, address_as_ip = find_address(interface_name)
    used_ips = {
        ipaddress.ip_address(ip.split("/")[0]) for ip in find_using_ips(wg_output)
    }
    used_ips.add(address_as_ip)
    new_ip = find_unused_ip(used_ips, address)
    return f"{new_ip}/32"


def make_new_config_file(address: str, private_key: str, sever_public_key: str) -> str:
    """Make new config file with exclusive DNS address."""
    config = textwrap.dedent(
        f"""\
            [Interface]
            Address = {address}
            PrivateKey = {private_key}
            DNS = {DNS}
             
            [Peer]
            PublicKey = {sever_public_key}
            AllowedIPs = 0.0.0.0/0
            Endpoint = {ADDRESS}"""
    )
    return config


def make_qr_code(username: str) -> None:
    """Make a QR-Code for scanning by mobile apps by running:
    `qrencode -o <username>.png < >username>.conf`"""
    # You must install "qrencode"!
    subprocess.call(f"qrencode -o {username}.png < {username}.conf", shell=True)


def make_configs(
    username: str, ip: str, private_key: str, server_public_key: str
) -> None:
    """Make a new directory with name of <username> and add config and QR-Code into that."""
    config = make_new_config_file(ip, private_key, server_public_key)

    os.mkdir(username)
    os.chdir(username)

    with open(f"{username}.conf", "w", encoding="utf-8") as file:
        file.write(config)

    make_qr_code(username)


def insert_new_peer(public_key: str, allowed_ips: str, interface_name: str) -> None:
    """Insert new peer by running: `wg set <config file name
    (e.g. wg0)> peer <public key> allowed-ips <allowed-ips>`"""
    process = subprocess.call(
        ["wg", "set", interface_name, "peer", public_key, "allowed-ips", allowed_ips],
        stdout=subprocess.DEVNULL,
    )
    assert process == 0, "inserting new peer failed."


def save_new_config(interface_name: str) -> None:
    """
    This function save the configs by running `wg-quick save <interface (e.g. wg0)>`
    """
    process = subprocess.call(
        ["wg-quick", "save", interface_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert process == 0, "saving new config failed."


def main() -> None:
    """
    Main entry point.
    """
    wg_show_output = get_wg_show_output()
    interface_name = find_interface(wg_show_output)
    server_public_key = find_server_public_key(wg_show_output)
    username = get_user()  # Get username.
    private_key = gen_private_key()  # Generate private key.
    public_key = gen_public_key(
        private_key
    )  # Generate public key based on private key.
    ip = make_new_ip(interface_name, wg_show_output)  # Get a new allowed-ip.
    make_configs(username, ip, private_key, server_public_key)  # Make the configs.
    # If everything ran without any errors, now we insert
    # the peer in our config file (no need to reload wireguard).
    insert_new_peer(public_key, ip, interface_name)
    save_new_config(interface_name)  # Save the new configs.


if __name__ == "__main__":
    check_requirements()
    main()
