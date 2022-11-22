# robotframework-output-stream

A custom output for Robot Framework enabling realtime analysis in a more compact format.

## Important

The current version is still pre-alpha and the format specified below may still change. 

## Details

Its implementation is based on a listener, so, it's possible to
use it in any Robot Framework run by using the `--listener` argument.

## Installation

Install with:

`pip install robotframework-output-stream`

## Usage

  `python -m robot -l NONE -r NONE -o NONE --listener robot_out_stream.RFStream:--dir=<dir_to_output>:--max-file-size=<5m>:--max-files=<5>:--log=<log.html>`

  Note: the `-l NONE and -r NONE -o NONE` arguments are recommended to disable the standard Robot Framework output (since
  the `RFStream` should cover all its use-cases).

  Arguments:

  `--dir`
  
    Points to a directory where the output files should be written.
    (default: '.' -- i.e.: working dir).
    
    Note: if a ':' is used it should be changed to <COLON> (because a ':'
    char is used as the separator by Robot Framework).
    So, something as `c:/temp/foo` should be written as `c<COLON>/temp/foo`.
    
    Example:
    
      --dir=./output
      --dir=c<COLON>/temp/output

  `--max-file-size`
  
    Specifies the maximum file size before a rotation for the output file occurs.
    
    The size can be specified with its unit.
    The following units are supported: `gb, g, mb, m, kb, k, b`
    (to support gigabytes=gb or g, megabytes=mb or m, kilobytes=kb or k, bytes=b).
    
    Note: if no unit is specified, it's considered as bytes.
    
    Example:
    
      --max-file-size=200kb
      --max-file-size=2mb
      --max-file-size=1gb
      --max-file-size=10000b

  `--max-files`
  
    Specifies the maximum number of files to be generated in the logging before
    starting to prune old files.
    
    i.e.: If `--max-files=2`, it will generate `output.rfstream`, `output_2.rfstream`
    and when `output_3.rfstream` is about to be generated it'll erase `output.rfstream`.
    
    Example:
    
      --max-files=3

  `--log`
  
    If specified writes html contents which enables the log contents to be
    viewed embedded in an html file.
    It should point to a path in the filesystem.
    
    Note: if a ':' is used it should be changed to <COLON> (because a ':'
    char is used as the separator by Robot Framework).
    So, something as `c:/temp/log.html` should be written as `c<COLON>/temp/log.html`.
    
    Note: the contents embedded in the file will contain the files written on disk
    but embedded as a compressed information (so, its size should be less than
    the size of the contents on disk), note that contents prunned from the log
    (due to the --max-files setting) will NOT appear in the log.html.
    
    Example:
    
      --log=./logs/log.html
      --log=c<COLON>/temp/log.html


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

The basic log can actually be splitted to multiple files.
Such files are splitted in the following files (the idea
is that it can be split when it becomes too big).

- `output.rfstream`
- `output_2.rfstream`
- `output_3.rfstream`
- ...

The file should be always written and flushed at each log entry and
it should be consistent even if the process crashes in the meanwhile
(meaning that all entries written are valid up to the point of the crash).

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

    Identifies the version of the log being used
    
    Example:
    
    `V 1`             - Identifies version 1 of the log

### I: Info(info_as_json_string)

    Example:
    
    `I "python=3.7"`
    `I "RF=5.7.0"`

### M: Memorize name(id ':' json_string)

    Example:

    `M a:"Start Suite"`    - Identifies the String 'Start Suite' as 'a' in the logs 
    `M b:"End Suite"`      - Identifies the String 'End Suite' as 'b' in the logs

### T: Initial time(isoformat)

    Example:
    
    `T 2022-10-03T11:30:54.927`

### SS: Start Suite

    Spec: `name:oid, suite_id:oid, suite_source:oid, time_delta_in_seconds:float`
    
    Note: references to oid mean a reference to a previously memorized name.
    
    Note: the time may be given as -1 (if unknown -- later it may be provided
    through an "S" message to specify the start time which may be useful
    when converting to xml where the status only appears later on in the file
    along with the status and not at the suite definition).
    
    Example (were a, b and c are references to previously memorized names):
    
    `SS a|b|c|0.333`

## RS: Replay Start Suite

    Same as "SS" but used just to replay the content to specify the context
    when the log starts being written in a new file.

### ES: End Suite

    Spec: `status:oid, time_delta_in_seconds:float`
    
    Note: the status (PASS, FAIL, SKIP) is a previously memorized name.
    
    Example:
    
    `ES a|0.222`

### ST: Start Task/test

    Spec: `name:oid, suite_id:oid, lineno:int, time_delta_in_seconds:float`
    
    Note: the source (filename) is available through the parent suite_source.
    
    Example:
    
    `ST a|b|22|0.332`

## RT: Replay Start Task/test

    Same as "ST" but used just to replay the content to specify the context
    when the log starts being written in a new file.


### ET: End Task/Test

    Spec: `status:oid, message:oid, time_delta_in_seconds:float`
    
    Example:
    
    `ET a|b|0.332`

### SK: Start Keyword

    Spec: `name:oid, libname:oid, keyword_type:oid, doc:oid, source:oid, lineno:int, time_delta_in_seconds:float`
    
    Example:
    
    `SK a|b|c|d|e|22|0.444`

## RK: Replay Keyword

    Same as "SK" but used just to replay the content to specify the context
    when the log starts being written in a new file.

### KA: Keyword argument

    Spec: `argument:oid`
    
    Example:
    
    `KA f`

### AS: Assign keyword call result to a variable

    Spec: `assign:oid`
    
    Example:
    
    `AS f`

### EK: End Keyword

    Spec: `status:oid, time_delta_in_seconds:float`
    
    Example:
    
    `EK a|0.333`

### L: Provide a log message

    Spec: `level:level_enum, message:oid, time_delta_in_seconds:float`
    
    level_enum is:
    - ERROR = `E`
    - FAIL = `F`
    - INFO = `I`
    - WARN = `W`
    
    Example:
    
    `L E|a|0.123`

### S: Specify the start time (of the containing suite/test/task/keyword)

    Spec: `start_time_delta:float`
    
    Example:
    
    `S 2.456`

### TG: Apply tag

    Spec: `tag:oid`
    
    Example:
    
    `TG a`

