# Dependencies (Python packages)

If your robot project requires dependencies such as Python packages,
you should define them in the `conda.yaml` file in this directory. Robocloud
Worker will use `conda.yaml` file to set up a conda environment when executed
in a target environment.

For a local environment, you can use `pip` or `conda` or another preferred
package manager to install the dependencies. Keep the `conda.yaml` in sync with
the required dependencies. Otherwise, the robot might work when run locally,
but not when run using Robocloud Worker.

If you do not want to use conda at all and want to provide the execution
environment yourself, you can delete the `conda.yaml` file.