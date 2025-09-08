---
author: Svetlozar Georgiev
title: Setting up GitHub Actions for CMake/C++ Projects
date: 2020-08-15T12:42:35+01:00
draft: false
---

I have been using [Travis CI](https://travis-ci.com/) for my open source projects hosted on GitHub. Travis CI is great! Very easy to set up and most importantly *free*. However, since I usually try to write portable code, I like testing my C++ projects on multiple operating systems. Travis CI's Linux images and testing are great, however their Windows support - [unfortunately not so much](https://docs.travis-ci.com/user/reference/windows/). According to their docs

> [...] our Windows environment is in early stages and a minimal subset of what’s available on Linux or macOS is currently supported.

So for my Windows CI needs I have been using [Appveyor](https://www.appveyor.com/) which is also great, however that means maintaining and worrying about two CI configurations. Additionally, Travis's Linux images (even Ubuntu 20.04) ship with the default packages which means we get a [pretty old version of cmake - 3.12](https://docs.travis-ci.com/user/reference/focal/#compilers-and-build-toolchain)! I personally needed to use at least 3.16 as it introduced precompiled headers (and unity builds!). Because of that, some extra steps are needed to set up the build environment:

`.travis.yml`:

```yaml
before_install:
  - DEPS_DIR="${TRAVIS_BUILD_DIR}/deps"
  - mkdir ${DEPS_DIR} && cd ${DEPS_DIR}
  - travis_retry wget --no-check-certificate https://github.com/Kitware/CMake/releases/download/v3.16.0-rc2/cmake-3.16.0-rc2-Linux-x86_64.tar.gz
  - tar -xvf cmake-3.16.0-rc2-Linux-x86_64.tar.gz > /dev/null
  - mv cmake-3.16.0-rc2-Linux-x86_64 cmake-install
  - PATH=${DEPS_DIR}/cmake-install:${DEPS_DIR}/cmake-install/bin:$PATH
  - cd ${TRAVIS_BUILD_DIR}
```

This is not the end of the world, but I would like to have a cleaner configuration.

## GitHub Actions

I have been meaning to switch to GitHub Actions for a while now since they provide both Windows and Linux images (and MacOS if you care about it). That would mean I would have a single script controlling my CI. Additionally, the [pre-installed packages](https://docs.github.com/en/actions/reference/software-installed-on-github-hosted-runners) seem to be newer versions. Looking at the docs, we can see we have CMake 3.16 on Linux and 3.18 on Windows! For compilers, we have gcc 9.3 on Linux and Visual Studio 2019 on Linux (16.0).

I am not saying GitHub actions are perfect. It seems that they are still in development and bugs are still being fixed. Additionally, they are not completely free. You get 2000 minutes for the free version and 3000 for the PRO version per month. However, on Windows images, 1 real minute counts as 2!

I have GitHub PRO so I will get 3000 minutes per month which sounds reasonable, however, if I decide to set up CI for another project, I might run out of time pretty quickly.

### Setting up GitHub Actions

To start setting an action up, create `.github/workflows/<action_name>.yml` in the root of your repo.

The project I am configuring is a C++ project with a few submodules and can be built with CMake. The project lives [here](https://github.com/Ligh7bringer/Hazel). I also like using `ninja` which looking at the docs seems to be missing from the list of preinstalled packages. No worries, we can add it easily!

Let's start populating our `push.yml` file.

First we add our build matrix:

```yaml
name: Build Project

on: [push, pull_request]

jobs:
  build:
    name: ${{ matrix.config.name }}
    runs-on: ${{ matrix.config.os }}
    strategy:
      fail-fast: false
      matrix:
        config:
        - {
            name: "Windows Latest - MSVC", artifact: "windows-msvc.tar.xz",
            os: windows-latest,
            cc: "cl", cxx: "cl",
          }
        - {
            name: "Ubuntu Latest - GCC", artifact: "linux-gcc.tar.xz",
            os: ubuntu-latest,
            cc: "gcc-9", cxx: "g++-9"
          }
        - {
            name: "Ubuntu Latest - Clang", artifact: "linux-clang.tar.xz",
            os: ubuntu-latest,
            cc: "clang-9", cxx: "clang++-9"
          }
```

Her's an explanation of what the sections mean:

- `name` is the name of our actions as it will appear on GitHub when it is running.

- `on` is the event that will trigger this action. I have set it up to trigger when I push to my repo.

- `matrix` is the different images (Operating systems want to use). Each config has a name and it will appear on GitHub when the action is running as a separate job. 

  - `os` is the image we want to use. I want to test my app on Windows and Linux so I have specified `ubuntu-latest` (Ubuntu 20.04 at the time of writing) and `windows-latest` (Windows Server 2019 at the time of writing).

  - `cc` and `cxx` these are custom "variables" that we specify so we can differentiate between the compilers we will be using in the build step.

Next, we add our build steps:

```yaml
    steps:
    - uses: actions/checkout@v2
      with:
        submodules: 'recursive'
    - uses: seanmiddleditch/gha-setup-ninja@master
```

- `uses` specifies that we are using an action someone else wrote to make our lives easier. `actions/checkout@v2` allows us to checkout our repository so that our action can access it. 
  - `with` allows us to specify an option for the action. Here I specify the `submodules` option and I set it to `recursive` so that my submodules are also checked out. Should be the equivalent of running `git submodule update --init --recursive`.
- We also use `seanmiddleditch/gha-setup-ninja@master` which downloads and adds `ninja` to the `PATH`.

Now we need to set up our environment. On Windows, we need to have `cl.exe` on our path se we can set it as the compiler for CMake to use. On Linux, we need to `apt install` some packages: 

```yaml
    - name: Set Windows ENV
      if: runner.os == 'Windows'
      uses: ilammy/msvc-dev-cmd@v1

    - name: Install Linux Dependencies
      if: runner.os == 'Linux'
      run: sudo apt install libxcursor-dev libxrandr-dev libxinerama-dev libxi-dev libglew-dev
```

- Each step has a `name` which will helpfully be shown on GitHub when the actions is running.

- `if` allows us to check if a condition is true. In this case, I am checking whether we are running on Windows or Linux.

  - on Windows, we add the `ilammy/msvc-dev-cmd@v1` action which will set up the build environment for us and add the path to `cl` to the `PATH`.

  - on Linux we just use `apt` to install our dependencies.

- `run` allows us to run a shell command. To run multiple commands the `yaml` syntax is a bit weird:

```yaml
run: |
  command_1
  command_2
  command_3
```

Now that we've set up our environment for both OSs, we can configure CMake and build our project:

```yaml
    - name: CMake Configure 
      run: cmake -Bbuild -GNinja -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=${{ matrix.config.cc }} -DCMAKE_CXX_COMPILER=${{ matrix.config.cxx }}

    - name: CMake Build
      run: cmake --build build
```

- `-Bbuild`: we tell CMake to create our `build` directory in the current directory.

- `-GNinja`: we tell CMake that we want to use `ninja` explicitly.

- `-DCMAKE_C_COMPILER=${{ matrix.config.cc }}` will use the `cc` value we set in the matrix to set our `C` compiler. We do the same for our `CXX` compiler: `-DCMAKE_CXX_COMPILER=${{ matrix.config.cxx }}`

- `cmake --build build`: and finally we build our project! CMake will automatically invoke `ninja` for us.

When this code is pushed to github, it will trigger the action automatically. We can go to the Actions tab to see the list of running jobs and their progress:

![actions status](/gh-actions-status.png)

My full `push.yml` can be seen [here](https://github.com/Ligh7bringer/Hazel/blob/master/.github/workflows/push.yml).

### Adding a status badge to `readme.md`

We can also add a status badge to our readme! It looks something like this:

![CI status](https://github.com/Ligh7bringer/Hazel/workflows/Build%20Hazel/badge.svg
)

We need to simply add the following to our `readme.md`:

```md
![CI status](https://github.com/<USER>/<REPO>/workflows/<WORKFLOW NAME>/badge.svg)
```

where

- `<USER>` is our username

- `<REPO>` is the name of our repository

- `<WORKFLOW_NAME>` is the name of our workflow. This is not the name of the file where we specified our workflow, but the value we set `name` to. In my case, it is `Build Project`. If it contains whitespace, we need to replace it with `%20`, so in my case it becomes `Build%20Project`:

```md
![CI status](https://github.com/Ligh7bringer/Hazel/workflows/Build%20Project/badge.svg)
```

## Future work

We can also set up automatic deployment of the built artifact but that is a matter for another post.
