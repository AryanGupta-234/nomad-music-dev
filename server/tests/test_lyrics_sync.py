from app.services.lyrics.sync import parse_lrc, active_index

def test_parse_lrc_and_active_index():
    lines = parse_lrc('[00:01.50]Hello\n[00:03.000]World')
    assert [x.time_ms for x in lines] == [1500, 3000]
    assert active_index(lines, 1499) == -1
    assert active_index(lines, 1500) == 0
    assert active_index(lines, 3200) == 1
