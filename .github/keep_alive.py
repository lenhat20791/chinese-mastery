from playwright.sync_api import sync_playwright

APP_URL = "https://tutienhsk.streamlit.app/"
WAKE_BUTTON = "button:has-text('get this app back up')"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)

        # App đang ngủ: bấm nút đánh thức
        try:
            page.click(WAKE_BUTTON, timeout=15000)
            print("App đang ngủ, đã bấm nút đánh thức.")
        except Exception:
            print("App đang thức.")

        # Giữ kết nối trình duyệt đủ lâu để Streamlit tính là có truy cập
        page.wait_for_timeout(45000)
        browser.close()
    print("Hoàn tất.")


if __name__ == "__main__":
    main()
