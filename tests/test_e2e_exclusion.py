"""
E2E tests: exclusion flow using Playwright.

Prerequisites: streamlit run valu.py on localhost:8501

Usage:
  pytest tests/test_e2e_exclusion.py -v
  pytest tests/test_e2e_exclusion.py::test_comparables_display -v
"""
import time
import pytest
from playwright.sync_api import sync_playwright, Page

BASE_URL = "http://localhost:8501"
PROP_NAME = "Brown 2750"
PROP_URL = f"{BASE_URL}/?prop={PROP_NAME.replace(' ', '%20')}"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=300)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1400, "height": 900})
    page = ctx.new_page()
    page.set_default_timeout(20000)
    yield page
    ctx.close()


def wait(page: Page, secs=3):
    page.wait_for_load_state("networkidle")
    time.sleep(secs)


def open_expander(page: Page, label: str):
    summary = page.locator("summary").filter(has_text=label).first
    summary.wait_for(state="visible", timeout=10000)
    summary.click()
    page.wait_for_timeout(1500)


def test_navigate_via_query_param(page):
    """Smoke: direct ?prop= navigation works and shows property."""
    page.goto(PROP_URL)
    wait(page, 6)
    assert page.locator("body").inner_text().count(PROP_NAME) > 0


def test_comparables_display(page):
    """Comparables table appears when both expanders are open."""
    page.goto(PROP_URL)
    wait(page, 6)

    open_expander(page, "Comparables")
    open_expander(page, "Propiedades Comparables")

    n_comps = page.evaluate(
        "() => document.querySelectorAll('div[data-testid=\"stCheckbox\"]').length"
    )
    assert n_comps >= 2, f"Expected >=2 comparables, got {n_comps}"


def test_navigate_away_and_back(page):
    """Navigate away and back to property works."""
    page.goto(PROP_URL)
    wait(page, 6)

    back_btn = page.get_by_role("button", name="Volver al Portafolio").first
    back_btn.wait_for(state="visible", timeout=5000)
    back_btn.click()
    wait(page, 4)

    page.goto(PROP_URL)
    wait(page, 6)

    assert page.locator("body").inner_text().count(PROP_NAME) > 0
