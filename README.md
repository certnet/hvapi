## Hyper-V management python library

This small python library utilize Hyper-V powershell cmdlets and wmi api(in some cases) to provide simple asynchronous
python api for creation and management of Hyper-V virtual machines.

## Design

All operations performed via simple powershell scripts, executed using *asyncio.create_subprocess_exec*. I did not used
some native api, because there are lot of existing powershell code for working with Hyper-V, so it is much simpler just 
to copy-paste that code :smile:.

## Roadmap

* switch to some wmi library(most likely it will be native **.Net Microsoft.Management**  via **pythonnet** bindings, it
works faster than native python **wmi** package)
* add auto-generated documentation
* unit tests(maybe)

## License

The MIT License

Copyright (c) 2017 Eugene Chekanskiy, echekanskiy@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.