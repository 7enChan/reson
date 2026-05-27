import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobook_generator.core.m4b_exporter import M4BChapter, build_ffmetadata, export_m4b


class TestM4BExporter(unittest.TestCase):
    def test_build_ffmetadata_writes_book_and_chapter_metadata(self):
        chapters = [
            M4BChapter("序", Path("/tmp/000_序.mp3")),
            M4BChapter("1 世界生病了", Path("/tmp/001_1 世界生病了.mp3")),
        ]

        metadata = build_ffmetadata(
            "彻底的信仰，根本的疗愈",
            "杨定一",
            chapters,
            [1500, 2500],
        )

        self.assertIn(";FFMETADATA1", metadata)
        self.assertIn("title=彻底的信仰，根本的疗愈", metadata)
        self.assertIn("artist=杨定一", metadata)
        self.assertIn("album=彻底的信仰，根本的疗愈", metadata)
        self.assertIn("genre=Audiobook", metadata)
        self.assertIn("START=0\nEND=1500\ntitle=序", metadata)
        self.assertIn("START=1500\nEND=4000\ntitle=1 世界生病了", metadata)

    def test_build_ffmetadata_escapes_ffmetadata_reserved_characters(self):
        metadata = build_ffmetadata(
            "Title=Book;Edition#1",
            "Author\\Name",
            [M4BChapter("Chapter=1;Intro#A", Path("/tmp/chapter.mp3"))],
            [1000],
        )

        self.assertIn("title=Title\\=Book\\;Edition\\#1", metadata)
        self.assertIn("artist=Author\\\\Name", metadata)
        self.assertIn("title=Chapter\\=1\\;Intro\\#A", metadata)

    @patch("audiobook_generator.core.m4b_exporter._probe_duration_ms", return_value=1000)
    @patch("audiobook_generator.core.m4b_exporter.shutil.which")
    @patch("audiobook_generator.core.m4b_exporter.subprocess.run")
    def test_export_m4b_invokes_ffmpeg_with_metadata_and_chapters(
        self,
        mock_run,
        mock_which,
        _mock_probe,
    ):
        mock_which.side_effect = lambda name: f"/usr/local/bin/{name}"
        mock_run.return_value = MagicMock(stdout="")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            chapter_one = tmp_path / "000_序.mp3"
            chapter_two = tmp_path / "001_1 世界生病了.mp3"
            chapter_one.write_bytes(b"audio-one")
            chapter_two.write_bytes(b"audio-two")
            output_file = tmp_path / "book.m4b"

            export_m4b(
                [
                    M4BChapter("序", chapter_one),
                    M4BChapter("1 世界生病了", chapter_two),
                ],
                output_file,
                "Book",
                "Author",
            )

        command = mock_run.call_args.args[0]
        self.assertIn("-f", command)
        self.assertIn("ffmetadata", command)
        self.assertIn("-map_chapters", command)
        self.assertIn("1", command)
        self.assertIn("-c:a", command)
        self.assertIn("aac", command)
        self.assertEqual(str(output_file), command[-1])


if __name__ == "__main__":
    unittest.main()
