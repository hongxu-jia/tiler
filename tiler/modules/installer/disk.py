"""
Copyright (c) 2024 Wind River Systems, Inc.

SPDX-License-Identifier: Apache-2.0
"""

import logging
import os

from tiler.modules.base import ModuleBase
from tiler import utils


class Parted(ModuleBase):
    """Module that uses parted to create parttions."""

    def __init__(self, state, config, stage):
        self.state = state
        self.config = config
        self.stage = stage

        self.logging = logging.getLogger(__name__)
        self.device = self.config.params.disk
        self.slices = self.stage.slices

    def run(self):
        self.logging.info("Running parted.")

        self.logging.info("Creating gpt disk label.")
        utils.run_command(
            ["parted", self.device, "--script", "mklabel", "gpt"])

        self.logging.info("Creating parttiions.")
        for index, part in enumerate(self.slices, start=1):
            self.logging.info(f"Creating partition {index}: {part.name}")
            utils.run_command(
                ["parted", "-a", "optimal", "-s", self.device, "--", "mkpart",
                 part.name, part.start, part.end])
            if len(part.flags) != 0:
                for flag in part.flags:
                    utils.run_command(
                        ["parted", "-a", "optimal", "-s", self.device, "--",
                         "set", str(index), flag, "on"])


class Filesystem(ModuleBase):
    """Module that create filesystmes on parttions."""

    def __init__(self, state, config, stage):
        self.state = state
        self.config = config
        self.stage = stage

        self.logging = logging.getLogger(__name__)
        self.device = self.config.params.disk
        self.filesystems = self.stage.filesystems

    def run(self):
        self.logging.info("Running filesystems.")

        for index, part in enumerate(self.filesystems, start=1):
            fs = self._get_partition_device(index, self.device)
            if os.path.exists(fs):
                self._mkfs(fs, part.fs, part.label, part.name)

    def _mkfs(self, fs, fs_type, label, name):
        self.logging.info(f"Formatting filesystems for {name}.")

        if fs_type == "vfat":
            # vfat is a special case
            utils.run_command(
                ["mkfs.vfat", "-F", "32", "-n", label, fs])
        else:
            utils.run_command(
                ["mkfs", "-F", "-t", fs_type, "-L", label, fs])

    def _get_partition_device(self, number, device):
        """Get the parition device."""
        suffix = "p"
        # Check partition naming first: if used 'by-id'i naming convention
        if "/disk/by-id" in device:
            suffix = "-part"

        # If the iamge device has a digit as the last character, the partition
        # suffix is p<number> else it's just <number>
        last = device[len(device) - 1]
        if last >= "0" and last <= "9":
            return "%s%s%d" % (device, suffix, number)
        else:
            return "%s%d" % (device, number)
