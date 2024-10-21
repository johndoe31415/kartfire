# KArTFire
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

## Boundary conditions
Any testcase is defined by a JSON file that has the following form:

```json
{
	"action": "xyz",
	...
}
```

I.e., it needs to always be a dictionary that at least has an "action" key in
the top-level. The answer can be any valid JSON object. For example, these
would be valid testcases with their appropriate solutions:

```json
{
	"action": "add",
	"a": 4,
	"b": 5
}
```

Expected answer:

```json
{
	"sum": 9
}
```

## Execution
TODO

## License
GNU-GPL 3.
