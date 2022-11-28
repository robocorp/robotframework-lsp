def convert_in_memory(xml_output):
    import io
    from robot_out_stream.xml_to_rfstream import convert_xml_to_rfstream

    txt = xml_output.read_text("utf-8")

    source = io.StringIO()
    source.write(txt)
    source.seek(0)

    in_memory_contents = io.StringIO()

    def write(s):
        in_memory_contents.write(s)

    convert_xml_to_rfstream(source, write=write)
    in_memory_contents.seek(0)
    return in_memory_contents


def check(datadir, data_regression, name):
    from robot_out_stream import iter_decoded_log_format

    xml_output = datadir / name
    rf_stream_output = convert_in_memory(xml_output)

    rf_stream = []
    for line in iter_decoded_log_format(rf_stream_output):
        rf_stream.append(line)

    data_regression.check(rf_stream)
    for line in rf_stream:
        print(line)


def test_decode_output_1(datadir, data_regression):
    check(datadir, data_regression, "output_1.xml")


def test_decode_output_2(datadir, data_regression):
    check(datadir, data_regression, "output_2.xml")


def test_decode_output_3(datadir, data_regression):
    check(datadir, data_regression, "output_3.xml")


def test_decode_output_4(datadir, data_regression):
    check(datadir, data_regression, "output_4.xml")


def test_decode_output_5(datadir, data_regression):
    check(datadir, data_regression, "output_5.xml")


def test_decode_output_6(datadir, data_regression):
    check(datadir, data_regression, "output_6.xml")


def test_decode_output_7(datadir, data_regression):
    check(datadir, data_regression, "output_7.xml")


def test_decode_output_8(datadir, data_regression):
    check(datadir, data_regression, "output_8.xml")


def test_decode_output_9(datadir, data_regression):
    check(datadir, data_regression, "output_9.xml")


def test_decode_output_10(datadir, data_regression):
    check(datadir, data_regression, "output_10.xml")


def test_decode_output_11(datadir, data_regression):
    check(datadir, data_regression, "output_11.xml")
