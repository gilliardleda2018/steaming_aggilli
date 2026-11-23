import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "player" / "index.html").read_text(encoding="utf-8")
TIDY = HTML.split("/* AGGILLI_LIBRARY_TIDY_V1", 1)[1].split("</script>", 1)[0]


class LibraryTidyTests(unittest.TestCase):
    def test_tidy_runs_before_the_library_uses_the_catalog(self):
        self.assertLess(HTML.index("const libraryTidy="), HTML.index("let tracks=[];"))
        self.assertIn("const organized=libraryTidy.organize(data,{genres:serverGenres,saved:savedGenres});", HTML)

    def test_file_name_noise_is_removed(self):
        for fragment in (r"\[[A-Za-z0-9_-]{11}\]", r"\.f\d{2,4}\s*$", "official|oficial|video|audio"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, TIDY)

    def test_duplicates_are_hidden_and_saved_ids_follow_the_kept_copy(self):
        self.assertIn("alias.set(drop.t.track_id,keep.t.track_id);", TIDY)
        for remapped in ("favorites.add(id)", "recentIds=remap(recentIds);", "dailyHistory.ids=remap(dailyHistory.ids);",
                         "playlists.set(name,new Set(remap([...ids])));"):
            with self.subTest(remapped=remapped):
                self.assertIn(remapped, HTML)

    def test_listener_genre_edits_win_and_suggestions_are_not_persisted(self):
        self.assertIn("for(const [id,genre] of Object.entries(saved)){", TIDY)
        self.assertIn("savedGenres[t.track_id]=select.value;localStorage.setItem('aggilli-generos',JSON.stringify(savedGenres));", HTML)

    def test_suggested_genres_exist_in_the_player_filter(self):
        for genre in ("'Rock Progressivo'", "'Rock'", "'Eletronica'"):
            with self.subTest(genre=genre):
                self.assertIn(genre, TIDY)
                self.assertIn(genre, HTML.split("const genreNames=", 1)[1].split("];", 1)[0])

    def test_original_file_name_stays_searchable(self):
        self.assertIn("t.original?.title||''", HTML)


if __name__ == "__main__":
    unittest.main()
