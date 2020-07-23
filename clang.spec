%global compat_build 1

%global _smp_mflags -v -j8

%global maj_ver 10
%global min_ver 0
%global patch_ver 0
%global baserelease 1

%global download_url https://github.com/llvm/llvm-project/releases/download

%define _prefix /usr/local/tools/llvm-%{maj_ver}

%global clang_tools_binaries \
	%{_bindir}/clang-apply-replacements \
	%{_bindir}/clang-change-namespace \
	%{_bindir}/clang-check \
	%{_bindir}/clang-doc \
	%{_bindir}/clang-extdef-mapping \
	%{_bindir}/clang-format \
	%{_bindir}/clang-import-test \
	%{_bindir}/clang-include-fixer \
	%{_bindir}/clang-move \
	%{_bindir}/clang-offload-bundler \
	%{_bindir}/clang-offload-wrapper \
	%{_bindir}/clang-query \
	%{_bindir}/clang-refactor \
	%{_bindir}/clang-rename \
	%{_bindir}/clang-reorder-fields \
	%{_bindir}/clang-scan-deps \
	%{_bindir}/clang-tidy \
	%{_bindir}/clangd \
	%{_bindir}/diagtool \
	%{_bindir}/hmaptool \
	%{_bindir}/pp-trace

%global clang_binaries \
	%{_bindir}/clang \
	%{_bindir}/clang++ \
	%{_bindir}/clang-%{maj_ver} \
	%{_bindir}/clang++-%{maj_ver} \
	%{_bindir}/clang-cl \
	%{_bindir}/clang-cpp

%bcond_with python3

%global clang_srcdir clang-%{version}%{?rc_ver:rc%{rc_ver}}.src
%global clang_tools_srcdir clang-tools-extra-%{version}%{?rc_ver:rc%{rc_ver}}.src

Name:		clang-%{maj_ver}
Version:	%{maj_ver}.%{min_ver}.%{patch_ver}
Release:	%{baserelease}%{?dist}
Summary:	A C language family front-end for LLVM

License:	NCSA
URL:		http://llvm.org
Source0:	%{download_url}/llvmorg-%{version}/%{clang_srcdir}.tar.xz
Source1:	%{download_url}/llvmorg-%{version}/%{clang_tools_srcdir}.tar.xz
Source2:	%{download_url}/llvmorg-%{version}/%{clang_tools_srcdir}.tar.xz.sig
Source3:	%{download_url}/llvmorg-%{version}/%{clang_srcdir}.tar.xz.sig

BuildRequires:	gcc
BuildRequires:	gcc-c++
BuildRequires:	cmake
BuildRequires:	ninja-build

BuildRequires:	llvm-%{maj_ver}-devel = %{version}
BuildRequires:	llvm-%{maj_ver}-static = %{version}
BuildRequires:	libxml2-devel
BuildRequires:  libstdc++-static

BuildRequires:	perl-generators
BuildRequires:	ncurses-devel

BuildRequires:	python3-lit

BuildRequires:	libatomic

# We need python3-devel for pathfix.py.
BuildRequires:	python3-devel
BuildRequires: chrpath

Requires:	%{name}-libs%{?_isa} = %{version}-%{release}

# clang requires gcc, clang++ requires libstdc++-devel
# - https://bugzilla.redhat.com/show_bug.cgi?id=1021645
# - https://bugzilla.redhat.com/show_bug.cgi?id=1158594
Requires:	libstdc++-devel
Requires:	gcc-c++

Provides:	clang(major) = %{maj_ver}

Conflicts:	compiler-rt < %{version}
Conflicts:	compiler-rt > %{version}

%description
clang: noun
    1. A loud, resonant, metallic sound.
    2. The strident call of a crane or goose.
    3. C-language family front-end toolkit.

The goal of the Clang project is to create a new C, C++, Objective C
and Objective C++ front-end for the LLVM compiler. Its tools are built
as libraries and designed to be loosely-coupled and extensible.

%package libs
Summary: Runtime library for clang
Requires: compiler-rt-%{maj_ver}%{?_isa} = %{version}

%description libs
Runtime library for clang.

%package devel
Summary: Development header files for clang
Requires: %{name}%{?_isa} = %{version}-%{release}
# The clang CMake files reference tools from clang-tools-extra.
Requires: %{name}-tools-extra%{?_isa} = %{version}-%{release}
Requires: %{name}-libs = %{version}-%{release}

%description devel
Development header files for clang.

%package analyzer
Summary:	A source code analysis framework
License:	NCSA and MIT
BuildArch:	noarch
Requires:	%{name} = %{version}-%{release}
# not picked up automatically since files are currently not installed in
# standard Python hierarchies yet
Requires:	python

%description analyzer
The Clang Static Analyzer consists of both a source code analysis
framework and a standalone tool that finds bugs in C and Objective-C
programs. The standalone tool is invoked from the command-line, and is
intended to run in tandem with a build of a project or code base.

%package tools-extra
Summary:	Extra tools for clang
Requires: llvm-%{maj_ver}-libs%{?_isa} = %{version}
Requires: clang-%{maj_ver}-libs%{?_isa} = %{version}

%description tools-extra
A set of extra tools built using Clang's tooling API.

# Put git-clang-format in its own package, because it Requires git
# and we don't want to force users to install all those dependenices if they
# just want clang.
%package -n git-clang-format
Summary:	Integration of clang-format for git
Requires: %{name}%{?_isa} = %{version}-%{release}
Requires:	git
Requires:	python3

%description -n git-clang-format
clang-format integration for git.

%prep
%setup -T -q -b 1 -n %{clang_tools_srcdir}
%setup -q -n %{clang_srcdir}

%build

%if 0%{?__isa_bits} == 64
sed -i 's/\@FEDORA_LLVM_LIB_SUFFIX\@/64/g' test/lit.cfg.py
%else
sed -i 's/\@FEDORA_LLVM_LIB_SUFFIX\@//g' test/lit.cfg.py
%endif

mkdir -p _build
cd _build

%ifarch s390 s390x %{arm} %ix86 ppc64le
# Decrease debuginfo verbosity to reduce memory consumption during final library linking
%global optflags %(echo %{optflags} | sed 's/-g /-g1 /')
%endif

# -DCMAKE_INSTALL_RPATH=";" is a workaround for llvm manually setting the
# rpath of libraries and binaries.  llvm will skip the manual setting
# if CAMKE_INSTALL_RPATH is set to a value, but cmake interprets this value
# as nothing, so it sets the rpath to "" when installing.
cmake .. -G Ninja \
	-DLLVM_PARALLEL_LINK_JOBS=1 \
	-DLLVM_LINK_LLVM_DYLIB:BOOL=ON \
	-DCMAKE_BUILD_TYPE=RelWithDebInfo \
	-DLLVM_CONFIG:FILEPATH=%{_bindir}/llvm-config-%{__isa_bits} \
	-DPYTHON_EXECUTABLE=%{__python3} \
	-DCMAKE_INSTALL_RPATH:BOOL=";" \
	-DCMAKE_INSTALL_PREFIX=%{_prefix} \
%ifarch s390 s390x %{arm} %ix86 ppc64le
	-DCMAKE_C_FLAGS_RELWITHDEBINFO="%{optflags} -DNDEBUG" \
	-DCMAKE_CXX_FLAGS_RELWITHDEBINFO="%{optflags} -DNDEBUG" \
%endif
	-DCLANG_INCLUDE_TESTS:BOOL=OFF \
%if 0%{?__isa_bits} == 64
	-DLLVM_LIBDIR_SUFFIX=64 \
%else
	-DLLVM_LIBDIR_SUFFIX= \
%endif
	\
	-DLLVM_TABLEGEN_EXE:FILEPATH=%{_bindir}/llvm-tblgen \
	-DCLANG_ENABLE_ARCMT:BOOL=ON \
	-DCLANG_ENABLE_STATIC_ANALYZER:BOOL=ON \
	-DCLANG_INCLUDE_DOCS:BOOL=ON \
	-DCLANG_PLUGIN_SUPPORT:BOOL=ON \
	-DENABLE_LINKER_BUILD_ID:BOOL=ON \
	-DLLVM_ENABLE_EH=ON \
	-DLLVM_ENABLE_RTTI=ON \
	-DLLVM_BUILD_DOCS=ON \
%if 0%{?fedora}
	-DLLVM_ENABLE_SPHINX=ON \
%else
	-DLLVM_ENABLE_SPHINX=OFF \
%endif
	-DSPHINX_WARNINGS_AS_ERRORS=OFF \
	\
	-DCLANG_BUILD_EXAMPLES:BOOL=OFF \
	-DCLANG_REPOSITORY_STRING="%{?fedora:Fedora}%{?rhel:Red Hat} %{version}-%{release}" \
	-DLIB_SUFFIX=

ninja-build %{_smp_mflags}

%install
DESTDIR=%{buildroot} ninja-build %{_smp_mflags} install -C _build
ln -s clang++ %{buildroot}%{_bindir}/clang++-%{maj_ver}
# TODO: Package html docs
rm -vf %{buildroot}%{_datadir}/clang/clang-doc-default-stylesheet.css
rm -vf %{buildroot}%{_datadir}/clang/index.js
# remove editor integrations (bbedit, sublime, emacs, vim)
rm -vf %{buildroot}%{_datadir}/clang/clang-format-bbedit.applescript
rm -vf %{buildroot}%{_datadir}/clang/clang-format-sublime.py*
rm -vf %{buildroot}%{_datadir}/clang/clang-format.el
rm -vf %{buildroot}%{_datadir}/clang/clang-rename.el
# clang-tools-extra
rm -vf %{buildroot}%{_datadir}/clang/clang-include-fixer.el

%check
%if !0%{?compat_build}
# requires lit.py from LLVM utilities
# FIXME: Fix failing ARM tests, s390x i686 and ppc64le tests
# FIXME: Ignore test failures until rhbz#1715016 is fixed.
LD_LIBRARY_PATH=%{buildroot}%{_libdir} ninja-build -v check-all -j2 -C _build || \
%ifarch s390x i686 ppc64le %{arm}
:
%else
:
%endif

%endif

%files
%{_libdir}/clang/
%{clang_binaries}
%{_bindir}/c-index-test
%if 0%{?fedora}
%{_mandir}/man1/clang.1
%endif
%{_datadir}/clang/bash-autocomplete.sh

%files libs
%{_libdir}/*.so.*
%{_libdir}/*.so

%files devel
%{_libdir}/*.so
%{_libdir}/*.a
%{_includedir}/clang/
%{_includedir}/clang-c/
%{_libdir}/cmake/*
%dir %{_datadir}/clang/

%files analyzer
%{_bindir}/scan-view
%{_bindir}/scan-build
%{_libexecdir}/ccc-analyzer
%{_libexecdir}/c++-analyzer
%{_datadir}/scan-view/
%{_datadir}/scan-build/
%{_prefix}/share/man/man1/scan-build.1*

%files tools-extra
%{clang_tools_binaries}
%{_bindir}/find-all-symbols
%{_bindir}/modularize
#%{_mandir}/man1/diagtool.1.gz
%{_datadir}/clang/clang-format.py*
%{_datadir}/clang/clang-format-diff.py*
%{_datadir}/clang/clang-include-fixer.py*
%{_datadir}/clang/clang-tidy-diff.py*
%{_datadir}/clang/run-clang-tidy.py*
%{_datadir}/clang/run-find-all-symbols.py*
%{_datadir}/clang/clang-rename.py*

%files -n git-clang-format
%{_bindir}/git-clang-format

%changelog
* Tue Jul 21 2020 Evgeny Akhmetkhanov <axmetishe+llvm@gmail.com> - 10.0.0-1
- Initial spec for EL7 from FC33
