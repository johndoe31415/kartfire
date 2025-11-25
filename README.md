# 🛒🔥 KArTFire
kartfire is the "Known-Answer-Testing Framework". It is intended to run a
number of student's solutions inside a well-defined, network-isolated runtime
environment defined by a Docker container. The solutions can be
programming-language agnostic (i.e., compiled and interpreted languages are
supported, depending on the target container) and it is intended to deal with a
wide array of faulty solutions:

  * Solutions that do not produce any output or that produce unparsable output
  * Solutions that terminate with error codes
  * Solutions that consume unlimited memory
  * Solutions that do not terminate at all
  * Solutions that are deliberately hostile and try to trick the testing pipeline

kartfire maintains results as a SQLite database and keeps some (but not all)
failed testcases by default. This allows continuous testing and analysis of
performance over time without having crushingly large test files. It runs all
solutions inside a configurable Docker container, which allows the flexibility
to allow for prorgamming languages/runtime environments as desired. By default,
the Docker containers are executed without Internet connectivity to prevent
hostile solutions from exfiltrating testcases over the network or sideloading
unallowed dependencies.

An example of such a Docker container that allows for programs to be submitted
using the programming languges C, C++, Rust, Python, or Java can be found here:
[labwork-docker](https://github.com/johndoe31415/labwork-docker). An added
benefit of this type of code execution is that it allows students to precisely
test against the framework they will be evaluated under.

Additionally, kartfire has the ability to start up dependency containers so
that a testcase may entail asking the student's solution to connect to a
service and perform a specific task.


## Example
Testcases are given in JSON files such as the one that can be seen in
`example_testcases.json`. Essentially, every testcase has an `action` (which
tells the solution what to perform) and additionally arguments. The testcase
definition file may, but need not, contain the expected correct solution to the
problem. For example, a testcase file with only a single testcase may look like this:

```json
[
	{
		"action": "add",
		"arguments": {
			"a": 3,
			"b": 99
		},
		"correct_reply": {
			"sum": 102
		}
	}
]
```

To initialize a kartfire database, it needs to be created as an empty file first:

```
$ touch kartfire.sqlite3
```

Then, the testcase files can be imported:

```
$ kartfire import example_testcases.json
example_testcases.json: imported 5, skipped 0 duplicate testcases
```

The five example testcases are now inside the database but not yet contained in
any collection. Collections are essentially bundles of testcases. We may create
a new collection and add out testcases there. For example, we can query them by
action:

```
$ kartfire collection -D y my-collection @add
Collection "my-collection": 3 TCs, nominal runtime unknown
$ kartfire collection -D y my-collection @sub
Collection "my-collection": 4 TCs, nominal runtime unknown
$ kartfire collection -D y my-collection @mul
Collection "my-collection": 5 TCs, nominal runtime unknown
```

You can see that in the end, `my-collection` contains all five testcases.
However, kartfire has no idea yet as to how long it should take to execute
them. The nominal runtime is still unknown. For this purpose, we run a
known-good solution:

```
$ kartfire run my-collection solutions/good
1.1       good:55068607                  my-collection             [ref N/A lim N/A act 19 ms]            [++++++++++++++++++++++++++++++] All Pass 19 ms
========================================================================================================================
1.1       good:55068607                  my-collection             [ref N/A lim N/A act 19 ms]            [++++++++++++++++++++++++++++++] All Pass 19 ms
```

We can see that the testcases were executed and all tests of the good solution match the expected test vectors. We then mark this solution as the reference:

```
$ kartfire reference good
```

This marks the latest run of the solution called `good` as reference. When we now run it again:

```
$ kartfire run my-collection solutions/good
2.2       good:55068607                  my-collection             [ref 19 ms lim 3 sec act 20 ms]        [++++++++++++++++++++++++++++++] All Pass 20 ms
========================================================================================================================
2.2       good:55068607                  my-collection             [ref 19 ms lim 3 sec act 20 ms]        [++++++++++++++++++++++++++++++] All Pass 20 ms
```

We can see that it was executed in 20ms while the reference time was 19ms (from
the previous run) and the allowed maximum time was 3 seconds. By default, the
default permissible time before containers are forcefully shut down is `(3
seconds + 4 * ref_time)`. This can be customized using the `test_fixture.json`
configuration file.


## Client solution behavior
The client files are expected to be present in a directory. There are two scripts that are required in that file, one optional one and another mandatory one:

  - `build`: The build script is used to initially setup a solution, for
    example by compiling code. It is executed only once for each multirun, at
    the very start. A build script need not be present if the solution does not
    require one (e.g., for Python solutions).
  - `solution`: The actual program that is executed. It may be generated by the
    `build` script.

Both names are customizable. The `solution` script gets a single command line
parameter, which points to a JSON file. This JSON file contains the testcases
to be executed. The program is expected to print answers on the command line,
one line for each testcase, also in JSON format. For example, such a testcase
file could look like this:

```json
{
	"testcases": {
		"1": {
			"action": "add",
			"arguments": {
				"a": 3,
				"b": 99
			}
		},
		"2": {
			"action": "add",
			"arguments": {
				"a": 0,
				"b": 0
			}
		}
	}
}
```

A perfect solution might print the following on stdout:

```json
{"id": "1", "reply": {"sum": 102}}
{"id": "2", "reply": {"sum": 0}}
```


## Dependencies
Kartfire requires at least Docker v28, because for network isolation it uses
IPv6 only networks. IPv4 network bridges have the drawback that subnets are
limited, leading to the message: "Error response from daemon: all predefined
address pools have been fully subnetted". By using IPv6, this problem is
circumvented entirely.


## License
GNU-GPL 3.
