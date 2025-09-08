---
author: Svetlozar Georgiev
title: Building SYCL applications with CMake
date: 2020-01-31T21:05:17Z
draft: false
description: A quick (and dirty) tutorial on building SYCL applications with CMake 
---

When I started working at [Codeplay](https://www.codeplay.com/) one of the first things I was recommended to do was to learn SYCL. I quickly found out that there aren't that many resources online. I eventually found an example of the usual GPU "hello, world" program - vector addition. However, I realised I had no idea how to compile it! Well, here's a quick tutorial on compiling SYCL applications with CMake so you're not as confused as I was. I chose CMake since it's probably the fastest way to get something working.

All you should need to do this is:

- An editor (I am using Visual Studio Code)
- CMake (I am using version 3.16)
- [ComputeCPP](https://www.codeplay.com/products/computesuite/computecpp)

First, let's set up the project. My directory structure looks like this:

```bash
vecadd/
├── cmake/
├── CMakeLists.txt
└── src/
    └── main.cpp
```

Next, we need an actual program to compile. We are just going to copy one of the vector addition examples found online into **main.cpp**:

```c++
#include <CL/sycl.hpp>
#include <iostream>

class vector_addition;

int main(int argc, char **argv) {
  using namespace cl;

  // create vectors
  sycl::float4 a = {1.0, 2.0, 3.0, 4.0};
  sycl::float4 b = {4.0, 3.0, 2.0, 1.0};
  sycl::float4 c = {0.0, 0.0, 0.0, 0.0};

  // use default device selector
  sycl::default_selector selector;
  // create sycl queue
  sycl::queue queue(selector);

  // get device info
  std::cout << "Running on "
            << queue.get_device().get_info<sycl::info::device::name>()
            << "\n\n";

  /* set up buffers */
  {
    sycl::buffer<sycl::float4, 1> a_sycl(&a, sycl::range<1>(1));
    sycl::buffer<sycl::float4, 1> b_sycl(&b, sycl::range<1>(1));
    sycl::buffer<sycl::float4, 1> c_sycl(&c, sycl::range<1>(1));

    // create command  group
    queue.submit([&](sycl::handler &cgh) {
      // set up accessors
      auto a_acc = a_sycl.get_access<sycl::access::mode::read>(cgh);
      auto b_acc = b_sycl.get_access<sycl::access::mode::read>(cgh);
      auto c_acc = c_sycl.get_access<sycl::access::mode::discard_write>(cgh);

      // execute on device
      cgh.single_task<class vector_addition>(
          [=]() { c_acc[0] = a_acc[0] + b_acc[0]; });
    });
  }

  // show results
  std::cout << "  A { " << a.x() << ", " << a.y() << ", " << a.z() << ", "
            << a.w() << " }\n"
            << "+ B { " << b.x() << ", " << b.y() << ", " << b.z() << ", "
            << b.w() << " }\n"
            << "------------------\n"
            << "= C { " << c.x() << ", " << c.y() << ", " << c.z() << ", "
            << c.w() << " }" << std::endl;

  return 0;
}
```

To compile this code with **CMake** we will need to tell it how to find and use SYCL. To simplify this process, we can copy the necessary CMake files from the official [ComputeCpp samples repository](https://github.com/codeplaysoftware/computecpp-sdk). We are interested in the [cmake directory](https://github.com/codeplaysoftware/computecpp-sdk/tree/master/cmake) in the repository. The most important file is **FindComputeCpp.cmake** in the Modules directory (however, I recommend downloading the whole directory). This is what is going to allow us to find SYCL and the ComputeCpp compiler and link against the required libraries *without us having to do anything manually*.

We start populating our **CMakeLists.txt** file with the usual boilerplate:

```cmake
cmake_minimum_required(VERSION 3.4.3)
project(sycl-vecadd)
```

Then we need to tell CMake where to look for module configuration files. In our case, this is the **FindComputeCpp.cmake** file we just copied into the `cmake/` directory. We do this by adding the `cmake/Modules` directory to `CMAKE_MODULE_PATH`:

```cmake
list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/Modules)
```

Now CMake knows how to find ComputeCpp! We can find it with `find_package`:

```cmake
find_package(ComputeCpp REQUIRED)
```

CMake will display an error if it can't find it for some reason since we said it was `REQUIRED`.

Finally, we can create our executable:

```cmake
set(SOURCES src/main.cpp)

add_executable(vecadd ${SOURCES})
# enable c++14
target_compile_features(vecadd PRIVATE cxx_std_14)
```

The last step is to "add" SYCL to our executable. This is really easy since `add_sycl_to_target` was made available to us:

```cmake
add_sycl_to_target(TARGET vecadd SOURCES ${SOURCES})
```

Our finished **CMakeLists.txt** now looks like this:

```cmake
cmake_minimum_required(VERSION 3.4.3)
project(sycl-vecadd)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/Modules)

find_package(ComputeCpp REQUIRED)

set(SOURCES src/main.cpp)

add_executable(vecadd ${SOURCES})
# enable c++14
target_compile_features(vecadd PRIVATE cxx_std_14)

add_sycl_to_target(TARGET vecadd SOURCES ${SOURCES})
```

Now we can build our program! We create a build directory:

```bash
mkdir build && cd build
```

And we run CMake:

```bash
cmake -DComputeCpp_DIR=/path/to/computecpp/ ..
```

*Note* that we have to tell CMake where to find ComputeCpp. We set the `ComputeCpp_DIR` variable to point to the root directory of our ComputeCpp installation.

Finally, we compile our project:

```bash
cmake --build .
```

If we did everything right we should be able to run our executable:

```bash
./vecadd
```

And see the following output:

```bash
Running on Intel(R) Gen9 HD Graphics NEO

  A { 1, 2, 3, 4 }
+ B { 4, 3, 2, 1 }
------------------
= C { 5, 5, 5, 5 }
```
