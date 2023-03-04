def apply_completion(doc, completion, expect_additional_text_edits=True):
    text_edit = completion["textEdit"]
    additional_text_edits = completion.get("additionalTextEdits")
    if expect_additional_text_edits:
        assert additional_text_edits
    else:
        assert not additional_text_edits
    doc.apply_text_edits([text_edit])
    if additional_text_edits:
        doc.apply_text_edits(additional_text_edits)
