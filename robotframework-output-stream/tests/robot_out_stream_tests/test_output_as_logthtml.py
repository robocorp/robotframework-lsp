def test_output_as_loghtml(tmpdir, resources_dir):
    import os

    log_output = tmpdir / "log.html"
    outdir_to_listener = tmpdir / "out"
    max_file_size = "3MB"
    max_files = 2

    robot_file = os.path.join(resources_dir, "robot1.robot")

    replaced_outdir_to_listener = str(outdir_to_listener).replace(":", "<COLON>")
    replaced_log_output = str(log_output).replace(":", "<COLON>")

    import robot

    default_log_output = str(tmpdir / "log_original.html")
    default_xml_output = str(tmpdir / "out.xml")

    robot.run_cli(
        [
            "-l",
            default_log_output,
            "-r",
            "None",
            "-o",
            default_xml_output,
            "--listener",
            f"robot_out_stream.RFStream:--dir={replaced_outdir_to_listener}:--max-file-size={max_file_size}:--max-files={max_files}:--log={replaced_log_output}",
            str(robot_file),
        ],
        exit=False,
    )

    assert os.path.exists(log_output)
