def test_add_rois(BaseTestSequencer, test_roi_file_path):
    BaseTestSequencer.add_rois("AB", test_roi_file_path)

    for fc in BaseTestSequencer._get_fc_list():
        assert len(fc.ROIs) == 3
