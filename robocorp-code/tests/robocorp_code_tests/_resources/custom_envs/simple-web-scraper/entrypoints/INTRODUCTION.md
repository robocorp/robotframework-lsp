# Defining entrypoints

Define each entrypoint here as a script

- These are the scripts you select for activity in Robocorp Cloud
- Entrypoint scripts should not use any arguments
  > It is better to create scripts to contain the different argument variations
  > so that selecting an entrypoint in Robocorp Cloud remains clear

This directory will be in PATH when the bundle is executed in Robocorp Cloud Worker
or through Robocode CLI.
