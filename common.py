#!/usr/bin/env python3

import argparse
import collections
import copy
import datetime
import enum
import glob
import imp
import inspect
import json
import math
import multiprocessing
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib
import urllib.request

import cli_function
import shell_helpers
from shell_helpers import LF

common = sys.modules[__name__]

# Fixed parameters that don't depend on CLI arguments.
consts = {}
consts['repo_short_id'] = 'lkmc'
# https://stackoverflow.com/questions/20010199/how-to-determine-if-a-process-runs-inside-lxc-docker
consts['in_docker'] = os.path.exists('/.dockerenv')
consts['root_dir'] = os.path.dirname(os.path.abspath(__file__))
consts['data_dir'] = os.path.join(consts['root_dir'], 'data')
consts['p9_dir'] = os.path.join(consts['data_dir'], '9p')
consts['gem5_non_default_source_root_dir'] = os.path.join(consts['data_dir'], 'gem5')
if consts['in_docker']:
    consts['out_dir'] = os.path.join(consts['root_dir'], 'out.docker')
else:
    consts['out_dir'] = os.path.join(consts['root_dir'], 'out')
consts['readme'] = os.path.join(consts['root_dir'], 'README.adoc')
consts['readme_out'] = os.path.join(consts['out_dir'], 'README.html')
consts['build_doc_log'] = os.path.join(consts['out_dir'], 'build-doc.log')
consts['gem5_out_dir'] = os.path.join(consts['out_dir'], 'gem5')
consts['kernel_modules_build_base_dir'] = os.path.join(consts['out_dir'], 'kernel_modules')
consts['buildroot_out_dir'] = os.path.join(consts['out_dir'], 'buildroot')
consts['gem5_m5_build_dir'] = os.path.join(consts['out_dir'], 'util', 'm5')
consts['run_dir_base'] = os.path.join(consts['out_dir'], 'run')
consts['crosstool_ng_out_dir'] = os.path.join(consts['out_dir'], 'crosstool-ng')
consts['test_boot_benchmark_file'] = os.path.join(consts['out_dir'], 'test-boot.txt')
consts['packages_dir'] = os.path.join(consts['root_dir'], 'buildroot_packages')
consts['kernel_modules_subdir'] = 'kernel_modules'
consts['kernel_modules_source_dir'] = os.path.join(consts['root_dir'], consts['kernel_modules_subdir'])
consts['userland_subdir'] = 'userland'
consts['userland_source_dir'] = os.path.join(consts['root_dir'], consts['userland_subdir'])
consts['userland_build_ext'] = '.out'
consts['include_subdir'] = 'include'
consts['include_source_dir'] = os.path.join(consts['root_dir'], consts['include_subdir'])
consts['submodules_dir'] = os.path.join(consts['root_dir'], 'submodules')
consts['buildroot_source_dir'] = os.path.join(consts['submodules_dir'], 'buildroot')
consts['crosstool_ng_source_dir'] = os.path.join(consts['submodules_dir'], 'crosstool-ng')
consts['crosstool_ng_supported_archs'] = set(['arm', 'aarch64'])
consts['linux_source_dir'] = os.path.join(consts['submodules_dir'], 'linux')
consts['linux_config_dir'] = os.path.join(consts['root_dir'], 'linux_config')
consts['gem5_default_source_dir'] = os.path.join(consts['submodules_dir'], 'gem5')
consts['rootfs_overlay_dir'] = os.path.join(consts['root_dir'], 'rootfs_overlay')
consts['extract_vmlinux'] = os.path.join(consts['linux_source_dir'], 'scripts', 'extract-vmlinux')
consts['qemu_source_dir'] = os.path.join(consts['submodules_dir'], 'qemu')
consts['parsec_benchmark_source_dir'] = os.path.join(consts['submodules_dir'], 'parsec-benchmark')
consts['ccache_dir'] = os.path.join('/usr', 'lib', 'ccache')
consts['default_build_id'] = 'default'
consts['arch_short_to_long_dict'] = collections.OrderedDict([
    ('x', 'x86_64'),
    ('a', 'arm'),
    ('A', 'aarch64'),
])
# All long arch names.
consts['all_long_archs'] = [consts['arch_short_to_long_dict'][k] for k in consts['arch_short_to_long_dict']]
# All long and short arch names.
consts['arch_choices'] = set()
for key in consts['arch_short_to_long_dict']:
    consts['arch_choices'].add(key)
    consts['arch_choices'].add(consts['arch_short_to_long_dict'][key])
consts['default_arch'] = 'x86_64'
consts['gem5_cpt_prefix'] = '^cpt\.'
def git_sha(repo_path):
    return subprocess.check_output(['git', '-C', repo_path, 'log', '-1', '--format=%H']).decode().rstrip()
consts['sha'] = common.git_sha(consts['root_dir'])
consts['release_dir'] = os.path.join(consts['out_dir'], 'release')
consts['release_zip_file'] = os.path.join(consts['release_dir'], 'lkmc-{}.zip'.format(consts['sha']))
consts['github_repo_id'] = 'cirosantilli/linux-kernel-module-cheat'
consts['asm_ext'] = '.S'
consts['c_ext'] = '.c'
consts['cxx_ext'] = '.cpp'
consts['header_ext'] = '.h'
consts['kernel_module_ext'] = '.ko'
consts['obj_ext'] = '.o'
consts['userland_in_exts'] = [
    consts['asm_ext'],
    consts['c_ext'],
    consts['cxx_ext'],
]
consts['userland_out_exts'] = [
    consts['userland_build_ext'],
    consts['obj_ext'],
]
consts['config_file'] = os.path.join(consts['data_dir'], 'config.py')
consts['magic_fail_string'] = b'lkmc_test_fail'
consts['baremetal_lib_basename'] = 'lib'
consts['emulator_short_to_long_dict'] = collections.OrderedDict([
    ('q', 'qemu'),
    ('g', 'gem5'),
])
consts['all_long_emulators'] = [consts['emulator_short_to_long_dict'][k] for k in consts['emulator_short_to_long_dict']]
consts['emulator_choices'] = set()
for key in consts['emulator_short_to_long_dict']:
    consts['emulator_choices'].add(key)
    consts['emulator_choices'].add(consts['emulator_short_to_long_dict'][key])
consts['host_arch'] = platform.processor()

class LkmcCliFunction(cli_function.CliFunction):
    '''
    Common functionality shared across our CLI functions:

    * command timing
    * some common flags, e.g.: --arch, --dry-run, --quiet, --verbose
    '''
    def __init__(self, *args, defaults=None, supported_archs=None, **kwargs):
        '''
        :ptype defaults: Dict[str,Any]
        :param defaults: override the default value of an argument
        '''
        kwargs['config_file'] = consts['config_file']
        kwargs['extra_config_params'] = os.path.basename(inspect.getfile(self.__class__))
        if defaults is None:
            defaults = {}
        self._defaults = defaults
        self._is_common = True
        self._common_args = set()
        super().__init__(*args, **kwargs)
        self.supported_archs = supported_archs

        # Args for all scripts.
        arches = consts['arch_short_to_long_dict']
        arches_string = []
        for arch_short in arches:
            arch_long = arches[arch_short]
            arches_string.append('{} ({})'.format(arch_long, arch_short))
        arches_string = ', '.join(arches_string)
        self.add_argument(
            '-A',
            '--all-archs',
            default=False,
            help='''\
Run action for all supported --archs archs. Ignore --archs.
'''.format(arches_string)
        )
        self.add_argument(
            '-a',
            '--arch',
            action='append',
            choices=consts['arch_choices'],
            default=[consts['default_arch']],
            dest='archs',
            help='''\
CPU architecture to use. If given multiple times, run the action
for each arch sequentially in that order. If one of them fails, stop running.
Valid archs: {}
'''.format(arches_string)
        )
        self.add_argument(
            '--clang',
            default=False,
            help='''\
Build with clang as much as possible. Set the build-id to clang by default unless
one is given explicitly. Currently supported components: gem5.
'''
        )
        self.add_argument(
            '--dry-run',
            default=False,
            help='''\
Print the commands that would be run, but don't run them.

We aim display every command that modifies the filesystem state, and generate
Bash equivalents even for actions taken directly in Python without shelling out.

mkdir are generally omitted since those are obvious
'''
        )
        self.add_argument(
            '--gcc-which',
            choices=[
                'buildroot',
                'crosstool-ng',
                'host',
                'host-baremetal'
            ],
            default='buildroot',
            help='''\
Which toolchain binaries to use:
- buildroot: the ones we built with ./build-buildroot. For userland, links to glibc.
- crosstool-ng: the ones we built with ./build-crosstool-ng. For baremetal, links to newlib.
- host: the host distro pre-packaged userland ones. For userland, links to glibc.
- host-baremetal: the host distro pre-packaged bare one. For baremetal, links to newlib.
'''
        )
        self.add_argument(
            '--print-time',
            default=True,
            help='''\
Print how long it took to run the command at the end.
Implied by --quiet.
'''
        )
        self.add_argument(
            '-q',
            '--quiet',
            default=False,
            help='''\
Don't print anything to stdout, except if it is part of an interactive terminal.
TODO: implement fully, some stuff is escaping it currently.
'''
        )
        self.add_argument(
            '--quit-on-fail',
            default=True,
            help='''\
Stop running at the first failed test.
'''
        )
        self.add_argument(
            '-v',
            '--verbose',
            default=False,
            help='Show full compilation commands when they are not shown by default.'
        )

        # Gem5 args.
        self.add_argument(
            '--dp650', default=False,
            help='Use the ARM DP650 display processor instead of the default HDLCD on gem5.'
        )
        self.add_argument(
            '--gem5-build-dir',
            help='''\
Use the given directory as the gem5 build directory.
Ignore --gem5-build-id and --gem5-build-type.
'''
        )
        self.add_argument(
            '-M',
            '--gem5-build-id',
            help='''\
gem5 build ID. Allows you to keep multiple separate gem5 builds.
Default: {}
'''.format(consts['default_build_id'])
        )
        self.add_argument(
            '--gem5-build-type',
            default='opt',
            help='gem5 build type, most often used for "debug" builds.'
        )
        self.add_argument(
            '--gem5-source-dir',
            help='''\
Use the given directory as the gem5 source tree. Ignore `--gem5-worktree`.
'''
        )
        self.add_argument(
            '-N',
            '--gem5-worktree',
            help='''\
Create and use a git worktree of the gem5 submodule.
See: https://github.com/cirosantilli/linux-kernel-module-cheat#gem5-worktree
'''
        )

        # Linux kernel.
        self.add_argument(
            '--linux-build-dir',
            help='''\
Use the given directory as the Linux build directory. Ignore --linux-build-id.
'''
        )
        self.add_argument(
            '-L',
            '--linux-build-id',
            default=consts['default_build_id'],
            help='''\
Linux build ID. Allows you to keep multiple separate Linux builds.
'''
        )
        self.add_argument(
            '--linux-source-dir',
            help='''\
Use the given directory as the Linux source tree.
'''
        )
        self.add_argument(
            '--initramfs',
            default=False,
            help='''\
See: https://github.com/cirosantilli/linux-kernel-module-cheat#initramfs
'''
        )
        self.add_argument(
            '--initrd',
            default=False,
            help='''\
For Buildroot: create a CPIO root filessytem.
For QEMU use that CPUI root filesystem initrd instead of the default ext2.
See: https://github.com/cirosantilli/linux-kernel-module-cheat#initrd
'''
        )

        # Baremetal.
        self.add_argument(
            '-b',
            '--baremetal',
            help='''\
Use the given baremetal executable instead of the Linux kernel.

If the path is absolute, it is used as is.

If the path is relative, we assume that it points to a source code
inside baremetal/ and then try to use corresponding executable.
'''
        )

        # Buildroot.
        self.add_argument(
            '--buildroot-build-id',
            default=consts['default_build_id'],
            help='Buildroot build ID. Allows you to keep multiple separate gem5 builds.'
        )
        self.add_argument(
            '--buildroot-linux',
            default=False,
            help='Boot with the Buildroot Linux kernel instead of our custom built one. Mostly for sanity checks.'
        )

        # Android.
        self.add_argument(
            '--rootfs-type',
            default='buildroot',
            choices=('buildroot', 'android'),
            help='Which rootfs to use.'
        )
        self.add_argument(
            '--android-version', default='8.1.0_r60',
            help='Which android version to use. implies --rootfs-type android'
        )
        self.add_argument(
            '--android-base-dir',
            help='''\
If given, place all android sources and build files into the given directory.
One application of this is to put those large directories in your HD instead
of SSD.
'''
        )

        # crosstool-ng
        self.add_argument(
            '--crosstool-ng-build-id',
            default=consts['default_build_id'],
            help='Crosstool-NG build ID. Allows you to keep multiple separate crosstool-NG builds.'
        )
        self.add_argument(
            '--docker',
            default=False,
            help='''\
Use the docker download Ubuntu root filesystem instead of the default Buildroot one.
'''
        )

        # QEMU.
        self.add_argument(
            '-Q',
            '--qemu-build-id',
            default=consts['default_build_id'],
            help='QEMU build ID. Allows you to keep multiple separate QEMU builds.'
        )
        self.add_argument(
            '--qemu-which',
            choices=['lkmc', 'host'],
            default='lkmc',
            help='''\
Which qemu binaries to use: qemu-system-, qemu-, qemu-img, etc.:
- lkmc: the ones we built with ./build-qemu
- host: the host distro pre-packaged provided ones
'''
        )
        self.add_argument(
            '--machine',
            help='''\
Machine type:
* QEMU default: virt
* gem5 default: VExpress_GEM5_V1
'''
        )

        # Userland.
        self.add_argument(
            '--static',
            default=False,
            help='''\
Build userland executables statically. Set --userland-build-id to 'static'
if one was not given explicitly.
''',
        )
        self.add_argument(
            '-u', '--userland',
            help='''\
Run the given userland executable in user mode instead of booting the Linux kernel
in full system mode. In gem5, user mode is called Syscall Emulation (SE) mode and
uses se.py.
Path resolution is similar to --baremetal.
'''
        )
        self.add_argument(
            '--userland-args',
            help='''\
CLI arguments to pass to the userland executable.
'''
        )
        self.add_argument(
            '--userland-build-id'
        )

        # Run.
        self.add_argument(
            '-n', '--run-id', default='0',
            help='''\
ID for run outputs such as gem5's m5out. Allows you to do multiple runs,
and then inspect separate outputs later in different output directories.
'''
        )
        self.add_argument(
            '-P', '--prebuilt', default=False,
            help='''\
Use prebuilt packaged host utilities as much as possible instead
of the ones we built ourselves. Saves build time, but decreases
the likelihood of incompatibilities.
'''
        )
        self.add_argument(
            '--port-offset', type=int,
            help='''\
Increase the ports to be used such as for GDB by an offset to run multiple
instances in parallel. Default: the run ID (-n) if that is an integer, otherwise 0.
'''
        )

        # Misc.
        emulators = consts['emulator_short_to_long_dict']
        emulators_string = []
        for emulator_short in emulators:
            emulator_long = emulators[emulator_short]
            emulators_string.append('{} ({})'.format(emulator_long, emulator_short))
        emulators_string = ', '.join(emulators_string)
        self.add_argument(
            '--all-emulators', default=False,
            help='''\
Run action for all supported --emulators emulators. Ignore --emulators.
'''.format(emulators_string)
        )
        self.add_argument(
            '-e',
            '--emulator',
            action='append',
            choices=consts['emulator_choices'],
            default=['qemu'],
            dest='emulators',
            help='''\
Emulator to use. If given multiple times, semantics are similar to --arch.
Valid emulators: {}
'''.format(emulators_string)
        )
        self._is_common = False

    def __call__(self, *args, **kwargs):
        '''
        For Python code calls, in addition to base:

        - print the CLI equivalent of the call
        - automatically forward common arguments
        '''
        print_cmd = ['./' + self.extra_config_params, LF]
        for line in self.get_cli(**kwargs):
            print_cmd.extend(line)
            print_cmd.append(LF)
        if not ('quiet' in kwargs and kwargs['quiet']):
            shell_helpers.ShellHelpers().print_cmd(print_cmd)
        return super().__call__(**kwargs)

    def _init_env(self, env):
        '''
        Update the kwargs from the command line with values derived from them.
        '''
        def join(*paths):
            return os.path.join(*paths)
        if env['emulator'] in env['emulator_short_to_long_dict']:
            env['emulator'] = env['emulator_short_to_long_dict'][env['emulator']]
        if not env['_args_given']['userland_build_id']:
            if env['static']:
                env['userland_build_id'] = 'static'
            else:
                env['userland_build_id'] = env['default_build_id']
        if not env['_args_given']['gem5_build_id']:
            if env['_args_given']['gem5_worktree']:
                env['gem5_build_id'] = env['gem5_worktree']
            elif env['_args_given']['clang']:
                env['gem5_build_id'] = 'clang'
            else:
                env['gem5_build_id'] = consts['default_build_id']
        env['is_arm'] = False
        if env['arch'] == 'arm':
            env['armv'] = 7
            env['mcpu'] = 'cortex-a15'
            env['buildroot_toolchain_prefix'] = 'arm-buildroot-linux-gnueabihf'
            env['crosstool_ng_toolchain_prefix'] = 'arm-unknown-eabi'
            env['ubuntu_toolchain_prefix'] = 'arm-linux-gnueabihf'
            env['is_arm'] = True
        elif env['arch'] == 'aarch64':
            env['armv'] = 8
            env['mcpu'] = 'cortex-a57'
            env['buildroot_toolchain_prefix'] = 'aarch64-buildroot-linux-gnu'
            env['crosstool_ng_toolchain_prefix'] = 'aarch64-unknown-elf'
            env['ubuntu_toolchain_prefix'] = 'aarch64-linux-gnu'
            env['is_arm'] = True
        elif env['arch'] == 'x86_64':
            env['crosstool_ng_toolchain_prefix'] = 'x86_64-unknown-elf'
            env['gem5_arch'] = 'X86'
            env['buildroot_toolchain_prefix'] = 'x86_64-buildroot-linux-gnu'
            env['ubuntu_toolchain_prefix'] = 'x86_64-linux-gnu'
            if env['emulator'] == 'gem5':
                if not env['_args_given']['machine']:
                    env['machine'] = 'TODO'
            else:
                if not env['_args_given']['machine']:
                    env['machine'] = 'pc'
        if env['is_arm']:
            env['gem5_arch'] = 'ARM'
            if env['emulator'] == 'gem5':
                if not env['_args_given']['machine']:
                    if env['dp650']:
                        env['machine'] = 'VExpress_GEM5_V1_DPU'
                    else:
                        env['machine'] = 'VExpress_GEM5_V1'
            else:
                if not env['_args_given']['machine']:
                    env['machine'] = 'virt'
                    if env['arch'] == 'arm':
                        # highmem=off needed since v3.0.0 due to:
                        # http://lists.nongnu.org/archive/html/qemu-discuss/2018-08/msg00034.html
                        env['machine2'] = 'highmem=off'
                    elif env['arch'] == 'aarch64':
                        env['machine2'] = 'gic_version=3'
        else:
            env['machine2'] = None

        # Buildroot
        env['buildroot_build_dir'] = join(env['buildroot_out_dir'], 'build', env['buildroot_build_id'], env['arch'])
        env['buildroot_download_dir'] = join(env['buildroot_out_dir'], 'download')
        env['buildroot_config_file'] = join(env['buildroot_build_dir'], '.config')
        env['buildroot_build_build_dir'] = join(env['buildroot_build_dir'], 'build')
        env['buildroot_linux_build_dir'] = join(env['buildroot_build_build_dir'], 'linux-custom')
        env['buildroot_vmlinux'] = join(env['buildroot_linux_build_dir'], 'vmlinux')
        env['buildroot_host_dir'] = join(env['buildroot_build_dir'], 'host')
        env['buildroot_host_bin_dir'] = join(env['buildroot_host_dir'], 'usr', 'bin')
        env['buildroot_pkg_config'] = join(env['buildroot_host_bin_dir'], 'pkg-config')
        env['buildroot_images_dir'] = join(env['buildroot_build_dir'], 'images')
        env['buildroot_rootfs_raw_file'] = join(env['buildroot_images_dir'], 'rootfs.ext2')
        env['buildroot_qcow2_file'] = env['buildroot_rootfs_raw_file'] + '.qcow2'
        env['buildroot_cpio'] = join(env['buildroot_images_dir'], 'rootfs.cpio')
        env['staging_dir'] = join(env['out_dir'], 'staging', env['arch'])
        env['buildroot_staging_dir'] = join(env['buildroot_build_dir'], 'staging')
        env['buildroot_target_dir'] = join(env['buildroot_build_dir'], 'target')
        if not env['_args_given']['linux_source_dir']:
            env['linux_source_dir'] = os.path.join(consts['submodules_dir'], 'linux')
        common.extract_vmlinux = os.path.join(env['linux_source_dir'], 'scripts', 'extract-vmlinux')
        env['linux_buildroot_build_dir'] = join(env['buildroot_build_build_dir'], 'linux-custom')

        # QEMU
        env['qemu_build_dir'] = join(env['out_dir'], 'qemu', env['qemu_build_id'])
        env['qemu_executable_basename'] = 'qemu-system-{}'.format(env['arch'])
        env['qemu_executable'] = join(env['qemu_build_dir'], '{}-softmmu'.format(env['arch']), env['qemu_executable_basename'])
        env['qemu_img_basename'] = 'qemu-img'
        env['qemu_img_executable'] = join(env['qemu_build_dir'], env['qemu_img_basename'])

        # gem5
        if not env['_args_given']['gem5_build_dir']:
            env['gem5_build_dir'] = join(env['gem5_out_dir'], env['gem5_build_id'], env['gem5_build_type'])
        env['gem5_fake_iso'] = join(env['gem5_out_dir'], 'fake.iso')
        env['gem5_m5term'] = join(env['gem5_build_dir'], 'm5term')
        env['gem5_build_build_dir'] = join(env['gem5_build_dir'], 'build')
        env['gem5_executable_dir'] = join(env['gem5_build_build_dir'], env['gem5_arch'])
        env['gem5_executable_suffix'] = '.{}'.format(env['gem5_build_type'])
        env['gem5_executable'] = self.get_gem5_target_path(env, 'gem5')
        env['gem5_unit_test_target'] = self.get_gem5_target_path(env, 'unittests')
        env['gem5_system_dir'] = join(env['gem5_build_dir'], 'system')

        # gem5 source
        if env['_args_given']['gem5_source_dir']:
            assert os.path.exists(env['gem5_source_dir'])
        else:
            if env['_args_given']['gem5_worktree']:
                env['gem5_source_dir'] = join(env['gem5_non_default_source_root_dir'], env['gem5_worktree'])
            else:
                env['gem5_source_dir'] = env['gem5_default_source_dir']
        env['gem5_m5_source_dir'] = join(env['gem5_source_dir'], 'util', 'm5')
        env['gem5_config_dir'] = join(env['gem5_source_dir'], 'configs')
        env['gem5_se_file'] = join(env['gem5_config_dir'], 'example', 'se.py')
        env['gem5_fs_file'] = join(env['gem5_config_dir'], 'example', 'fs.py')

        # crosstool-ng
        env['crosstool_ng_buildid_dir'] = join(env['crosstool_ng_out_dir'], 'build', env['crosstool_ng_build_id'])
        env['crosstool_ng_install_dir'] = join(env['crosstool_ng_buildid_dir'], 'install', env['arch'])
        env['crosstool_ng_bin_dir'] = join(env['crosstool_ng_install_dir'], 'bin')
        env['crosstool_ng_util_dir'] = join(env['crosstool_ng_buildid_dir'], 'util')
        env['crosstool_ng_config'] = join(env['crosstool_ng_util_dir'], '.config')
        env['crosstool_ng_defconfig'] = join(env['crosstool_ng_util_dir'], 'defconfig')
        env['crosstool_ng_executable'] = join(env['crosstool_ng_util_dir'], 'ct-ng')
        env['crosstool_ng_build_dir'] = join(env['crosstool_ng_buildid_dir'], 'build')
        env['crosstool_ng_download_dir'] = join(env['crosstool_ng_out_dir'], 'download')

        # run
        env['gem5_run_dir'] = join(env['run_dir_base'], 'gem5', env['arch'], str(env['run_id']))
        env['m5out_dir'] = join(env['gem5_run_dir'], 'm5out')
        env['stats_file'] = join(env['m5out_dir'], 'stats.txt')
        env['gem5_trace_txt_file'] = join(env['m5out_dir'], 'trace.txt')
        env['gem5_guest_terminal_file'] = join(env['m5out_dir'], 'system.terminal')
        env['gem5_readfile'] = join(env['gem5_run_dir'], 'readfile')
        env['gem5_termout_file'] = join(env['gem5_run_dir'], 'termout.txt')
        env['qemu_run_dir'] = join(env['run_dir_base'], 'qemu', env['arch'], str(env['run_id']))
        env['qemu_termout_file'] = join(env['qemu_run_dir'], 'termout.txt')
        env['qemu_trace_basename'] = 'trace.bin'
        env['qemu_trace_file'] = join(env['qemu_run_dir'], 'trace.bin')
        env['qemu_trace_txt_file'] = join(env['qemu_run_dir'], 'trace.txt')
        env['qemu_rrfile'] = join(env['qemu_run_dir'], 'rrfile')
        env['gem5_out_dir'] = join(env['out_dir'], 'gem5')

        # Ports
        if not env['_args_given']['port_offset']:
            try:
                env['port_offset'] = int(env['run_id'])
            except ValueError:
                env['port_offset'] = 0
        if env['emulator'] == 'gem5':
            env['gem5_telnet_port'] = 3456 + env['port_offset']
            env['gdb_port'] = 7000 + env['port_offset']
        else:
            env['qemu_base_port'] = 45454 + 10 * env['port_offset']
            env['qemu_monitor_port'] = env['qemu_base_port'] + 0
            env['qemu_hostfwd_generic_port'] = env['qemu_base_port'] + 1
            env['qemu_hostfwd_ssh_port'] = env['qemu_base_port'] + 2
            env['qemu_gdb_port'] = env['qemu_base_port'] + 3
            env['extra_serial_port'] = env['qemu_base_port'] + 4
            env['gdb_port'] = env['qemu_gdb_port']
            env['qemu_background_serial_file'] = join(env['qemu_run_dir'], 'background.log')

        # gem5 QEMU polymorphism.
        if env['emulator'] == 'gem5':
            env['executable'] = env['gem5_executable']
            env['run_dir'] = env['gem5_run_dir']
            env['termout_file'] = env['gem5_termout_file']
            env['guest_terminal_file'] = env['gem5_guest_terminal_file']
            env['trace_txt_file'] = env['gem5_trace_txt_file']
        else:
            env['executable'] = env['qemu_executable']
            env['run_dir'] = env['qemu_run_dir']
            env['termout_file'] = env['qemu_termout_file']
            env['guest_terminal_file'] = env['qemu_termout_file']
            env['trace_txt_file'] = env['qemu_trace_txt_file']
        env['run_cmd_file'] = join(env['run_dir'], 'run.sh')

        # Linux kernel.
        if not env['_args_given']['linux_build_dir']:
            env['linux_build_dir'] = join(env['out_dir'], 'linux', env['linux_build_id'], env['arch'])
        env['lkmc_vmlinux'] = join(env['linux_build_dir'], 'vmlinux')
        if env['arch'] == 'arm':
            env['android_arch'] = 'arm'
            env['linux_arch'] = 'arm'
            env['linux_image_prefix'] = join('arch', env['linux_arch'], 'boot', 'zImage')
        elif env['arch'] == 'aarch64':
            env['android_arch'] = 'arm64'
            env['linux_arch'] = 'arm64'
            env['linux_image_prefix'] = join('arch', env['linux_arch'], 'boot', 'Image')
        elif env['arch'] == 'x86_64':
            env['android_arch'] = 'x86_64'
            env['linux_arch'] = 'x86'
            env['linux_image_prefix'] = join('arch', env['linux_arch'], 'boot', 'bzImage')
        env['lkmc_linux_image'] = join(env['linux_build_dir'], env['linux_image_prefix'])
        env['buildroot_linux_image'] = join(env['buildroot_linux_build_dir'], env['linux_image_prefix'])
        if env['buildroot_linux']:
            env['vmlinux'] = env['buildroot_vmlinux']
            env['linux_image'] = env['buildroot_linux_image']
        else:
            env['vmlinux'] = env['lkmc_vmlinux']
            env['linux_image'] = env['lkmc_linux_image']
        env['linux_config'] = join(env['linux_build_dir'], '.config')
        if env['emulator']== 'gem5':
            env['userland_quit_cmd'] = '/gem5_exit.sh'
        else:
            env['userland_quit_cmd'] = '/poweroff.out'
        env['ramfs'] = env['initrd'] or env['initramfs']
        if env['ramfs']:
            env['initarg'] = 'rdinit'
        else:
            env['initarg'] = 'init'
        env['quit_init'] = '{}={}'.format(env['initarg'], env['userland_quit_cmd'])

        # Kernel modules.
        env['kernel_modules_build_dir'] = join(env['kernel_modules_build_base_dir'], env['arch'])
        env['kernel_modules_build_subdir'] = join(env['kernel_modules_build_dir'], env['kernel_modules_subdir'])
        env['kernel_modules_build_host_dir'] = join(env['kernel_modules_build_base_dir'], 'host')
        env['kernel_modules_build_host_subdir'] = join(env['kernel_modules_build_host_dir'], env['kernel_modules_subdir'])
        env['userland_build_dir'] = join(env['out_dir'], 'userland', env['userland_build_id'], env['arch'])
        env['out_rootfs_overlay_dir'] = join(env['out_dir'], 'rootfs_overlay', env['arch'])
        env['out_rootfs_overlay_bin_dir'] = join(env['out_rootfs_overlay_dir'], 'bin')

        # Baremetal.
        env['baremetal_source_dir'] = join(env['root_dir'], 'baremetal')
        env['baremetal_source_arch_subpath'] = join('arch', env['arch'])
        env['baremetal_source_arch_dir'] = join(env['baremetal_source_dir'], env['baremetal_source_arch_subpath'])
        env['baremetal_source_lib_dir'] = join(env['baremetal_source_dir'], env['baremetal_lib_basename'])
        env['baremetal_link_script'] = os.path.join(env['baremetal_source_dir'], 'link.ld')
        if env['emulator'] == 'gem5':
            env['simulator_name'] = 'gem5'
        else:
            env['simulator_name'] = 'qemu'
        env['baremetal_build_dir'] = join(env['out_dir'], 'baremetal', env['arch'], env['simulator_name'], env['machine'])
        env['baremetal_build_lib_dir'] = join(env['baremetal_build_dir'], env['baremetal_lib_basename'])
        env['baremetal_build_ext'] = '.elf'

        # Userland / baremetal common source.
        env['common_basename_noext'] = 'lkmc'
        env['common_c'] = common_c = os.path.join(
            env['root_dir'],
            env['common_basename_noext'] + env['c_ext']
        )
        env['common_h'] = common_c = os.path.join(
            env['root_dir'],
            env['common_basename_noext'] + env['header_ext']
        )

        # Docker
        env['docker_build_dir'] = join(env['out_dir'], 'docker', env['arch'])
        env['docker_tar_dir'] = join(env['docker_build_dir'], 'export')
        env['docker_tar_file'] = join(env['docker_build_dir'], 'export.tar')
        env['docker_rootfs_raw_file'] = join(env['docker_build_dir'], 'export.ext2')
        env['docker_qcow2_file'] = join(env['docker_rootfs_raw_file'] + '.qcow2')
        if env['docker']:
            env['rootfs_raw_file'] = env['docker_rootfs_raw_file']
            env['qcow2_file'] = env['docker_qcow2_file']
        else:
            env['rootfs_raw_file'] = env['buildroot_rootfs_raw_file']
            env['qcow2_file'] = env['buildroot_qcow2_file']

        # Image
        if env['_args_given']['baremetal']:
            env['disk_image'] = env['gem5_fake_iso']
            if env['baremetal'] == 'all':
                path = env['baremetal']
            else:
                path = self.resolve_executable(
                    env['baremetal'],
                    env['baremetal_source_dir'],
                    env['baremetal_build_dir'],
                    env['baremetal_build_ext'],
                )
                source_path_noext = os.path.splitext(join(
                    env['baremetal_source_dir'],
                    os.path.relpath(path, env['baremetal_build_dir'])
                ))[0]
                for ext in [env['c_ext'], env['asm_ext']]:
                    source_path = source_path_noext + ext
                    if os.path.exists(source_path):
                        env['source_path'] = source_path
                        break
            env['image'] = path
        else:
            if env['emulator'] == 'gem5':
                env['image'] = env['vmlinux']
                if env['ramfs']:
                    env['disk_image'] = env['gem5_fake_iso']
                else:
                    env['disk_image'] = env['rootfs_raw_file']
            else:
                env['image'] = env['linux_image']
                env['disk_image'] = env['qcow2_file']

        # Android
        if not env['_args_given']['android_base_dir']:
            env['android_base_dir'] = join(env['out_dir'], 'android')
        env['android_dir'] = join(env['android_base_dir'], env['android_version'])
        env['android_build_dir'] = join(env['android_dir'], 'out')
        env['repo_path'] = join(env['android_base_dir'], 'repo')
        env['repo_path_base64'] = env['repo_path'] + '.base64'
        env['android_shell_setup'] = '''\
. build/envsetup.sh
lunch aosp_{}-eng
'''.format(self.env['android_arch'])

        # Toolchain.
        if not env['_args_given']['gcc_which']:
            if env['baremetal']:
                env['gcc_which'] = 'crosstool-ng'
        if env['gcc_which'] == 'buildroot':
            env['toolchain_prefix'] = os.path.join(
                env['buildroot_host_bin_dir'],
                env['buildroot_toolchain_prefix']
            )
            env['userland_library_dir'] = env['buildroot_target_dir']
        elif env['gcc_which'] == 'crosstool-ng':
            env['toolchain_prefix'] = os.path.join(
                env['crosstool_ng_bin_dir'],
                env['crosstool_ng_toolchain_prefix']
            )
        elif env['gcc_which'] == 'host':
            env['toolchain_prefix'] = env['ubuntu_toolchain_prefix']
            if env['arch'] == 'x86_64':
                env['userland_library_dir'] = '/'
            elif env['arch'] == 'arm':
                env['userland_library_dir'] = '/usr/arm-linux-gnueabihf'
            elif env['arch'] == 'aarch64':
                env['userland_library_dir'] = '/usr/aarch64-linux-gnu/'
        elif env['gcc_which'] == 'host-baremetal':
            if env['arch'] == 'arm':
                env['toolchain_prefix'] = 'arm-none-eabi'
            else:
                raise Exception('There is no host baremetal chain for arch: ' + env['arch'])
        else:
            raise Exception('Unknown toolchain: ' + env['gcc_which'])
        env['gcc'] = self.get_toolchain_tool('gcc')
        env['gxx'] = self.get_toolchain_tool('g++')

    def add_argument(self, *args, **kwargs):
        '''
        Also handle:

        - modified defaults from child classes.
        - common arguments to forward on Python calls
        '''
        shortname, longname, key, is_option = self.get_key(*args, **kwargs)
        if key in self._defaults:
            kwargs['default'] = self._defaults[key]
        if self._is_common:
            self._common_args.add(key)
        super().add_argument(*args, **kwargs)

    def get_elf_entry(self, elf_file_path):
        readelf_header = subprocess.check_output([
            self.get_toolchain_tool('readelf'),
            '-h',
            elf_file_path
        ])
        for line in readelf_header.decode().split('\n'):
            split = line.split()
            if line.startswith('  Entry point address:'):
                addr = line.split()[-1]
                break
        return int(addr, 0)

    @staticmethod
    def get_gem5_target_path(env, name):
        '''
        Get the magic gem5 target path form the meaningful component name.
        '''
        return os.path.join(env['gem5_executable_dir'], name + env['gem5_executable_suffix'])

    def gem5_list_checkpoint_dirs(self):
        '''
        List checkpoint directory, oldest first.
        '''
        prefix_re = re.compile(self.env['gem5_cpt_prefix'])
        files = list(filter(
            lambda x: os.path.isdir(os.path.join(self.env['m5out_dir'], x))
                      and prefix_re.search(x), os.listdir(self.env['m5out_dir'])
        ))
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.env['m5out_dir'], x)))
        return files

    def get_common_args(self):
        '''
        These are arguments that might be used by more than one script,
        and are all defined in this class instead of in the derived class
        of the script.
        '''
        return {
            key:self.env[key] for key in self._common_args if self.env['_args_given'][key]
        }

    def get_stats(self, stat_re=None, stats_file=None):
        if stat_re is None:
            stat_re = '^system.cpu[0-9]*.numCycles$'
        if stats_file is None:
            stats_file = self.env['stats_file']
        stat_re = re.compile(stat_re)
        ret = []
        with open(stats_file, 'r') as statfile:
            for line in statfile:
                if line[0] != '-':
                    cols = line.split()
                    if len(cols) > 1 and stat_re.search(cols[0]):
                        ret.append(cols[1])
        return ret

    def get_toolchain_tool(self, tool):
        return '{}-{}'.format(self.env['toolchain_prefix'], tool)

    def github_make_request(
            self,
            authenticate=False,
            data=None,
            extra_headers=None,
            path='',
            subdomain='api',
            url_params=None,
            **extra_request_args
        ):
        if extra_headers is None:
            extra_headers = {}
        headers = {'Accept': 'application/vnd.github.v3+json'}
        headers.update(extra_headers)
        if authenticate:
            headers['Authorization'] = 'token ' + os.environ['LKMC_GITHUB_TOKEN']
        if url_params is not None:
            path += '?' + urllib.parse.urlencode(url_params)
        request = urllib.request.Request(
            'https://' + subdomain + '.github.com/repos/' + self.env['github_repo_id'] + path,
            headers=headers,
            data=data,
            **extra_request_args
        )
        response_body = urllib.request.urlopen(request).read().decode()
        if response_body:
            _json = json.loads(response_body)
        else:
            _json = {}
        return _json

    def import_path(self, basename):
        '''
        https://stackoverflow.com/questions/2601047/import-a-python-module-without-the-py-extension
        https://stackoverflow.com/questions/31773310/what-does-the-first-argument-of-the-imp-load-source-method-do
        '''
        return imp.load_source(basename.replace('-', '_'), os.path.join(self.env['root_dir'], basename))

    def import_path_main(self, path):
        '''
        Import an object of the Main class of a given file.

        By convention, we call the main object of all our CLI scripts as Main.
        '''
        return self.import_path(path).Main()

    def is_arch_supported(self, arch):
        return self.supported_archs is None or arch in self.supported_archs

    def log_error(self, msg):
        print('error: {}'.format(msg), file=sys.stdout)

    def log_info(self, msg='', flush=False, **kwargs):
        if not self.env['quiet']:
            print('{}'.format(msg), **kwargs)
        if flush:
            sys.stdout.flush()

    def main(self, *args, **kwargs):
        '''
        Run timed_main across all selected archs and emulators.

        :return: if any of the timed_mains exits non-zero and non-null,
                 return that. Otherwise, return 0.
        '''
        env = kwargs.copy()
        self.input_args = env.copy()
        env.update(consts)
        real_all_archs = env['all_archs']
        if real_all_archs:
            real_archs = consts['all_long_archs']
        else:
            real_archs = env['archs']
        if env['all_emulators']:
            real_emulators = consts['all_long_emulators']
        else:
            real_emulators = env['emulators']
        return_value = 0
        class GetOutOfLoop(Exception): pass
        try:
            ret = self.setup()
            if ret is not None and ret != 0:
                return_value = ret
                raise GetOutOfLoop()
            for emulator in real_emulators:
                for arch in real_archs:
                    if arch in env['arch_short_to_long_dict']:
                        arch = env['arch_short_to_long_dict'][arch]
                    if self.is_arch_supported(arch):
                        if not env['dry_run']:
                            start_time = time.time()
                        env['arch'] = arch
                        env['archs'] = [arch]
                        env['_args_given']['archs'] = True
                        env['all_archs'] = False
                        env['emulator'] = emulator
                        env['emulators'] = [emulator]
                        env['_args_given']['emulators'] = True
                        env['all_emulators'] = False
                        self.env = env.copy()
                        self._init_env(self.env)
                        self.sh = shell_helpers.ShellHelpers(
                            dry_run=self.env['dry_run'],
                            quiet=self.env['quiet'],
                        )
                        ret = self.timed_main()
                        if not env['dry_run']:
                            end_time = time.time()
                            self.ellapsed_seconds = end_time - start_time
                            self.print_time(self.ellapsed_seconds)
                        if ret is not None and ret != 0:
                            return_value = ret
                            if self.env['quit_on_fail']:
                                raise GetOutOfLoop()
                    elif not real_all_archs:
                        raise Exception('Unsupported arch for this action: ' + arch)

        except GetOutOfLoop:
            pass
        ret = self.teardown()
        if ret is not None and ret != 0:
            return_value = ret
        return return_value

    def make_build_dirs(self):
        os.makedirs(self.env['buildroot_build_build_dir'], exist_ok=True)
        os.makedirs(self.env['gem5_build_dir'], exist_ok=True)
        os.makedirs(self.env['out_rootfs_overlay_dir'], exist_ok=True)

    def make_run_dirs(self):
        '''
        Make directories required for the run.
        The user could nuke those anytime between runs to try and clean things up.
        '''
        os.makedirs(self.env['gem5_run_dir'], exist_ok=True)
        os.makedirs(self.env['p9_dir'], exist_ok=True)
        os.makedirs(self.env['qemu_run_dir'], exist_ok=True)

    @staticmethod
    def seconds_to_hms(seconds):
        '''
        Seconds to hour:minute:seconds

        :ptype seconds: float
        :rtype: str

        https://stackoverflow.com/questions/775049/how-do-i-convert-seconds-to-hours-minutes-and-seconds 
        '''
        frac, whole = math.modf(seconds)
        hours, rem = divmod(whole, 3600)
        minutes, seconds = divmod(rem, 60)
        return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

    def print_time(self, ellapsed_seconds):
        if self.env['print_time'] and not self.env['quiet']:
            print('time {}'.format(self.seconds_to_hms(ellapsed_seconds)))

    def raw_to_qcow2(self, qemu_which=False, reverse=False):
        if qemu_which == 'host' or not os.path.exists(self.env['qemu_img_executable']):
            disable_trace = []
            qemu_img_executable = self.env['qemu_img_basename']
        else:
            # Prevent qemu-img from generating trace files like QEMU. Disgusting.
            disable_trace = ['-T', 'pr_manager_run,file=/dev/null', LF]
            qemu_img_executable = self.env['qemu_img_executable']
        infmt = 'raw'
        outfmt = 'qcow2'
        infile = self.env['rootfs_raw_file']
        outfile = self.env['qcow2_file']
        if reverse:
            tmp = infmt
            infmt = outfmt
            outfmt = tmp
            tmp = infile
            infile = outfile
            outfile = tmp
        self.sh.run_cmd(
            [
                qemu_img_executable, LF,
            ] +
            disable_trace +
            [
                'convert', LF,
                '-f', infmt, LF,
                '-O', outfmt, LF,
                infile, LF,
                outfile, LF,
            ]
        )

    @staticmethod
    def resolve_args(defaults, args, extra_args):
        if extra_args is None:
            extra_args = {}
        argcopy = copy.copy(args)
        argcopy.__dict__ = dict(list(defaults.items()) + list(argcopy.__dict__.items()) + list(extra_args.items()))
        return argcopy

    def resolve_source(self, in_path, magic_in_dir, in_exts):
        '''
        Convert a path-like string to a source file to the full source path,
        e.g. all follogin work and to do the same:

        - hello
        - hello.
        - hello.c
        - userland/hello
        - userland/hello.
        - userland/hello.c
        - /full/path/to/userland/hello
        - /full/path/to/userland/hello.
        - /full/path/to/userland/hello.c

        Also works on directories:

        - arch
        - userland/arch
        - /full/path/to/userland/arch
        '''
        if os.path.isabs(in_path):
            return in_path
        else:
            paths = [
                os.path.join(magic_in_dir, in_path),
                os.path.join(
                    magic_in_dir,
                    os.path.relpath(in_path, magic_in_dir),
                )
            ]
            for path in paths:
                name, ext = os.path.splitext(path)
                if len(ext) > 1:
                    try_exts = [ext]
                else:
                    try_exts = in_exts + ['']
                for in_ext in try_exts:
                    path = name + in_ext
                    if os.path.exists(path):
                        return path
            if not self.env['dry_run']:
                raise Exception('Source file not found for input: ' + in_path)

    def resolve_executable(self, in_path, magic_in_dir, magic_out_dir, out_ext):
        if os.path.isabs(in_path):
            return in_path
        else:
            paths = [
                os.path.join(magic_out_dir, in_path),
                os.path.join(
                    magic_out_dir,
                    os.path.relpath(in_path, magic_in_dir),
                )
            ]
            for path in paths:
                path = os.path.splitext(path)[0] + out_ext
                if os.path.exists(path):
                    return path
            if not self.env['dry_run']:
                raise Exception('Executable file not found. Tried:\n' + '\n'.join(paths))

    def resolve_userland_executable(self, path):
        '''
        Convert an userland source path-like string to an
        absolute userland build output path.
        '''
        return self.resolve_executable(
            path,
            self.env['userland_source_dir'],
            self.env['userland_build_dir'],
            self.env['userland_build_ext'],
        )

    def resolve_userland_source(self, path):
        return self.resolve_source(
            path,
            self.env['userland_source_dir'],
            self.env['userland_in_exts']
        )

    def setup(self):
        '''
        Similar to timed_main, but gets run only once for all --arch and --emulator,
        before timed_main.

        Different from __init__, since at this point env has already been calculated,
        so variables that don't depend on --arch or --emulator can be used.
        '''
        pass

    def timed_main(self):
        '''
        Main action of the derived class.

        Gets run once for every --arch and every --emulator.
        '''
        pass

    def teardown(self):
        '''
        Similar to setup, but run after timed_main.
        '''
        pass

class BuildCliFunction(LkmcCliFunction):
    '''
    A CLI function with common facilities to build stuff, e.g.:

    * `--clean` to clean the build directory
    * `--nproc` to set he number of build threads
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument(
            '--clean',
            default=False,
            help='Clean the build instead of building.',
        ),
        self.add_argument(
            '--force-rebuild',
            default=False,
            help='''\
Force rebuild even if sources didn't chage.
TODO: not yet implemented on all scripts.
'''
        )
        self.add_argument(
            '-j',
            '--nproc',
            default=multiprocessing.cpu_count(),
            type=int,
            help='Number of processors to use for the build.',
        )
        self.test_results = []

    def clean(self):
        build_dir = self.get_build_dir()
        if build_dir is not None:
            self.sh.rmrf(build_dir)

    def build(self):
        '''
        Do the actual main build work.
        '''
        raise NotImplementedError()

    def get_build_dir(self):
        return None

    def need_rebuild(self, srcs, dst):
        if self.env['force_rebuild']:
            return True
        if not os.path.exists(dst):
            return True
        for src in srcs:
            if os.path.getmtime(src) > os.path.getmtime(dst):
                return True
        return False

    def timed_main(self):
        '''
        Parse CLI, and to the build based on it.

        The actual build work is done by do_build in implementing classes.
        '''
        if self.env['clean']:
            return self.clean()
        else:
            return self.build()

# from aenum import Enum  # for the aenum version
TestResult = enum.Enum('TestResult', ['PASS', 'FAIL'])

class Test:
    def __init__(
        self,
        test_id: str,
        result : TestResult =None,
        ellapsed_seconds : float =None
    ):
        self.test_id = test_id
        self.result = result
        self.ellapsed_seconds = ellapsed_seconds
    def __str__(self):
        out = []
        if self.result is not None:
            out.append(self.result.name)
        if self.ellapsed_seconds is not None:
            out.append(LkmcCliFunction.seconds_to_hms(self.ellapsed_seconds))
        out.append(self.test_id)
        return ' '.join(out)

class TestCliFunction(LkmcCliFunction):
    '''
    Represents a CLI command that runs tests.

    Automates test reporting boilerplate for those commands.
    '''

    def __init__(self, *args, **kwargs):
        defaults = {
            'print_time': False,
        }
        if 'defaults' in kwargs:
            defaults.update(kwargs['defaults'])
        kwargs['defaults'] = defaults
        super().__init__(*args, **kwargs)
        self.tests = []

    def run_test(self, run_obj, run_args=None, test_id=None):
        '''
        This is a setup / run / teardown setup for simple tests that just do a single run.

        More complex tests might need to run the steps separately, e.g. gdb tests
        must run multiple commands: one for the run and one GDB.

        :param run_obj: callable object
        :param run_args: arguments to be passed to the runnable object
        :param test_id: test identifier, to be added in addition to of arch and emulator ids
        '''
        if run_obj.is_arch_supported(self.env['arch']):
            if run_args is None:
                run_args = {}
            test_id_string = self.test_setup(test_id)
            exit_status = run_obj(**run_args)
            self.test_teardown(run_obj, exit_status, test_id_string)

    def test_setup(self, test_id):
        test_id_string = '{} {}'.format(self.env['emulator'], self.env['arch'])
        if test_id is not None:
            test_id_string += ' {}'.format(test_id)
        self.log_info('test_id {}'.format(test_id_string), flush=True)
        return test_id_string

    def test_teardown(self, run_obj, exit_status, test_id_string):
        if not self.env['dry_run']:
            if exit_status == 0:
                test_result = TestResult.PASS
            else:
                test_result = TestResult.FAIL
                if self.env['quit_on_fail']:
                    self.log_error('Test failed')
                    sys.exit(1)
            self.log_info('test_result {}'.format(test_result.name))
            ellapsed_seconds = run_obj.ellapsed_seconds
        else:
            test_result = None
            ellapsed_seconds = None
        self.log_info()
        self.tests.append(Test(test_id_string, test_result, ellapsed_seconds))

    def teardown(self):
        '''
        :return: 1 if any test failed, 0 otherwise
        '''
        self.log_info('Test result summary')
        passes = []
        fails = []
        for test in self.tests:
            if test.result in (TestResult.PASS, None):
                passes.append(test)
            else:
                fails.append(test)
        if passes:
            for test in passes:
                self.log_info(test)
        if fails:
            for test in fails:
                self.log_info(test)
            self.log_error('A test failed')
            return 1
        return 0
