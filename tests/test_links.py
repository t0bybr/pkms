"""Tests for link extraction"""

import pytest
from pkms.tools.link import extract_wikilinks


class TestLinkExtraction:
    def test_extract_simple_link(self):
        text = "See [[pizza]] for details."
        links = extract_wikilinks(text)

        assert len(links) == 1
        assert links[0]["target"] == "pizza"
        assert links[0]["raw"] == "[[pizza]]"

    def test_extract_link_with_display(self):
        text = "See [[pizza|Pizza Recipe]] for details."
        links = extract_wikilinks(text)

        assert len(links) == 1
        assert links[0]["target"] == "pizza"
        assert links[0]["display"] == "Pizza Recipe"

    def test_extract_multiple_links(self):
        text = "See [[pizza]] and [[pasta]] for Italian recipes."
        links = extract_wikilinks(text)

        assert len(links) == 2
        targets = [l["target"] for l in links]
        assert "pizza" in targets
        assert "pasta" in targets

    def test_extract_no_links(self):
        text = "This text has no wikilinks."
        links = extract_wikilinks(text)

        assert len(links) == 0

    def test_extract_with_context(self):
        text = "See [[pizza]] for details."
        links = extract_wikilinks(text)

        assert "context" in links[0]
        assert "pizza" in links[0]["context"]
