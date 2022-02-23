
Developing
-----------

To develop the `Robot Framework Language Server for Intellij`, download the sources
and head to the `robotframework-intellij` directory (where `gradlew` is located).

Then, verify if everything is ok by running the tests with: `gradlew test` (note:
a `python` executable must be in the `PATH`).  

Afterwards, it should be possible to just open the `robotframework-intellij` folder
in `Intellij` (the community edition is Ok).

Note that `robotframework-intellij` is mostly the integration of the `Robot Framework Language Server`
into `Intellij` and the actual implementation of most features reside in the 
`Robot Framework Language Server` itself.

See: [Contributing to Robot Framework Language Server](../../robotframework-ls/docs/contributing.md).
