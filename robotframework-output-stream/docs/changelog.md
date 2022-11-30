New in 0.0.2 (2022-11-30)
-----------------------------

- `LH` message type added to provide embedded html (i.e.: add images to log output).
- `ID` provides an id for the run and the part of the file (incremented when rotating the output). 

- `log.html` improvements:

  - Can filter out keywords with `NOT RUN` status.
  - Hides iteration nodes after the 50th iteration (only if marked as `PASS` or `NOT RUN`).
  - Embeds HTML contents from log entries with `html=true`. 


New in 0.0.1 (2022-11-22)
-----------------------------

### First release

- Note: pre-alpha for early adapters.
- Format may still change.
- Basic structure which allows to memoize strings and build suite/task,test/keyword scope.
- Provides status, time, rotating output, tags, keyword arguments.