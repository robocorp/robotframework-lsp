# robotframework-output-stream
A custom output for Robot Framework enabling realtime analysis in a more compact format.

## Details
It's implementation is based on a listener, so, it's possible to
install to use it in any Robot Framework run.

## Usage

  `python -m robot -l NONE -r NONE -o NONE --listener robot_out_stream.RFStream:--dir=<dir_to_output>:--port:<port>`

  Note: the `-l NONE and -r NONE -o NONE` are recommended to disable the standard Robot Framework output (since
  the RFStream should cover all its use-cases).

  Arguments:

  `--dir`
  
      Points to a directory where the output files should be written.
      (default: '.' -- i.e.: working dir).
      Note: if a ':' is used it should be changed to <COLON> (because a ':'
      char is used as the separator by Robot Framework).
      So, something as `c:\temp\foo` should be written as `c<COLON>\temp\foo`.

  `--port`
  
      A port to where the streamed contents should be sent (only connects to localhost).
      A server should be listening at that port to receive the streamed "Basic log" contents.


## Requirements

The requirements for the generated log files are the following:

1. Compact log:

    The files generated should be as compact as possible. Reading the file
    may require a separate application (although the idea is still trying
    to keep to ASCII instead of a binary format).

2. Log streaming:

    The log format should be suitable for streaming (so, it's possible to
    interpret the log while it's being written or up to the point a 
    Python VM crash happened).

3. Information:

    While the format of the log should be as compact as possible, it should 
    be able to provide the needed information to debug an issue, so,
    it must track almost all information currently available in the Robot 
    output.xml.

4. Log file rotation:

    If while being written a log becomes too big the log contents should be
    rotated to a separate file and it should be possible to specify a maximum
    size for the log (even if old information in the log is discarded in this
    case).


## Outputs

Given the requisites above, the idea is generating the following files while running:

1. `Basic log`

    The basic log can actually be splitted to multiple files.
    Such files are splitted in the following files (the idea
    is that it can be split when it becomes too big).

    - `output.0.rfstream`
    - `output.1.rfstream`
    - `output.2.rfstream`
    - ...

    The file should be always written and flushed at each log entry and
    it should be consistent even if the process crashes in the meanwhile
    (meaning that all entries written are valid up to the point of the crash).

2. `Errors log`

    Files in the same format pointing to where an error happened (it should
    be possible to derive a traceback from that information).
    
    - `robot_out_stream.error.0.rfstream`
    - `robot_out_stream.error.1.rfstream`
    
    After the processing finished a file is written with all the errors.

    - `robot_out_stream.errors.summary.rfstream`

    Note: for most users just the errors log should be enough, but if something
    isn't identified as an error, the "Basic log" should provide insight on
    what actually happened during the full run.


## "Basic log" spec

To keep the format compact, strings will be referenced by an id in the 
output and the output message types will be predetermined and referenced in the 
same way.

Times are referenced by the delta from the start.

Also, each message should use a single line in the log output where the prefix
is the message type and the arguments is either a message with ids/numbers 
separated by `|` or json-encoded strings.

Note that each output log file (even if splitted after the main one) should be
readable in a completely independent way, so, the starting scope should be 
replicated as well as the needed names to memorize.

Basic message types are:

### V: Version(name)

    Example:
    
    V 1                     - Identifies version 1 of the log
    
### I: Info(info_as_json_string)

    Example:
    
    I "python=3.7"
    I "RF=5.7.0"

### M: Memorize name(id, json_string)

    Example:

    M SS:"Start Suite"     - Identifies the String 'Start Suite' as 'SS' in the logs 
    M ES:"End Suite"      - Identifies the String 'End Suite' as 'ES' in the logs
    
### T: Initial time(isoformat)

    Example:
    
    T 2022-10-03T11:30:54.927

### SS: Start Suite(name_id, suite_id_id, suite_source_id, time_delta_in_seconds)

    Example:
    
    M 1:"My Suite"
    M 2:"my_suite"
    M 3:"c:/temp/foo/bar/my_suite.robot"
    SS 1|2|3|0.553

### ES: End Suite

### ST: Start Task/test

### ET: End Task/Test

### SK: Start Keyword

### EK: End Keyword
