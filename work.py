from DrissionPage import ChromiumPage, ChromiumOptions
import time
import sys
import random
import os

# -------------------- НАСТРОЙКИ --------------------
MY_EMAIL = "your_real_email@example.com"
MY_PASSWORD = "YourPassword123!"
BASE_URL = "https://vfsglobal.com"
TARGET_URL = "https://visa.vfsglobal.com/ago/en/bra/login"
MAX_ATTEMPTS = 3

# Прокси задаётся через переменную окружения PROXY (например, http://user:pass@host:port)
PROXY = os.environ.get("PROXY", "")
# ----------------------------------------------------

def handle_cookie_banner(page):
    print("Проверка куки-баннера OneTrust...")
    selectors = [
        '#onetrust-accept-btn-handler',
        '#onetrust-reject-all-handler',
        '#onetrust-pc-btn-handler',
        '.onetrust-close-btn-handler',
    ]
    for selector in selectors:
        try:
            btn = page.ele(selector, timeout=5)
            if btn:
                btn.click()
                print(f"Куки-баннер закрыт через '{selector}'.")
                time.sleep(1)
                return True
        except Exception as e:
            print(f"Ошибка при обработке {selector}: {e}")
    try:
        page.run_js("""
            var banner = document.getElementById('onetrust-banner-sdk');
            if (banner) banner.style.display = 'none';
        """)
        print("Баннер скрыт через JavaScript.")
        return True
    except:
        pass
    print("Куки-баннер не обнаружен или уже закрыт.")
    return False

def is_captcha_passed(page):
    token_input = page.ele('@name=cf-turnstile-response', timeout=0.1)
    if token_input:
        val = token_input.attr('value')
        if val and len(val) > 50:
            return True
    return False

def wait_for_captcha_token(page, timeout=90):
    print("Ожидание автоматического прохождения Cloudflare Turnstile...")
    for i in range(timeout):
        if is_captcha_passed(page):
            print("Cloudflare challenge пройден автоматически.")
            return True
        if i == 0:
            print("Если капча не прошла сама, скрипт перезапустится.")
        if i % 10 == 0:
            print(f"Ожидание токена... {i} сек.")
        time.sleep(1)
    print("Токен не получен за отведённое время.")
    return False

def clear_browser_data(page):
    print("Очистка кук браузера...")
    page.run_cdp('Network.clearBrowserCookies')
    print("Куки очищены.")

def clear_storages(page):
    page.run_js("""
        localStorage.clear();
        sessionStorage.clear();
    """)
    print("localStorage и sessionStorage очищены.")

def human_type(element, text, delay_min=0.05, delay_max=0.15):
    for char in text:
        element.input(char)
        time.sleep(random.uniform(delay_min, delay_max))
    time.sleep(0.3)

def solve_vfs_logic(page):
    print("Ожидание загрузки интерфейса...")
    time.sleep(2)
    handle_cookie_banner(page)

    print("Поиск контейнера <app-cloudflare-captcha-container>...")
    container = page.ele('tag:app-cloudflare-captcha-container', timeout=15)

    if not container:
        if is_captcha_passed(page):
            print("Контейнер капчи не найден, но токен присутствует. Капча пройдена.")
            return True
        else:
            print("Контейнер капчи не появился, токен отсутствует.")
            return False

    print("Контейнер капчи найден.")
    if is_captcha_passed(page):
        print("Токен уже присутствует, капча пройдена.")
        return True

    print("Токен отсутствует. Ожидание автоматического прохождения капчи...")
    return wait_for_captcha_token(page)

def attempt_login():
    """
    Одна попытка входа. Возвращает True при успехе, иначе False.
    Браузер всегда закрывается после выполнения (успех или неудача).
    """
    co = ChromiumOptions()
    co.set_argument('--disable-blink-features=AutomationControlled')
    co.set_argument('--start-maximized')
    co.set_argument('--force-device-scale-factor=1')
    co.set_argument('--no-sandbox')                 # для Linux/Docker
    co.set_argument('--disable-dev-shm-usage')

    if PROXY:
        co.set_argument(f'--proxy-server={PROXY}')
        print(f"Используется прокси: {PROXY}")

    page = ChromiumPage(co)

    try:
        page.get("about:blank")
        time.sleep(1)
        clear_browser_data(page)

        print(f"Переход на главную страницу: {BASE_URL}")
        page.get(BASE_URL)
        time.sleep(6)

        clear_storages(page)
        handle_cookie_banner(page)
        time.sleep(random.uniform(2, 4))

        print(f"Переход на страницу входа: {TARGET_URL}")
        page.get(TARGET_URL)
        time.sleep(8)

        if not solve_vfs_logic(page):
            print("Капча не пройдена.")
            return False

        print("Заполнение формы...")
        user = page.ele('css:input[formcontrolname="username"]', timeout=10)
        pw = page.ele('css:input[formcontrolname="password"]')
        if user and pw:
            user.click()
            human_type(user, MY_EMAIL)
            time.sleep(random.uniform(0.3, 0.7))
            pw.click()
            human_type(pw, MY_PASSWORD)
            time.sleep(random.uniform(0.5, 1.0))

            print("Клик по кнопке входа...")
            login_btn = page.ele('css:button[type="submit"]', timeout=5)
            if not login_btn:
                login_btn = page.ele('text=Sign In', timeout=3)
            if not login_btn:
                login_btn = page.ele('text=Login', timeout=3)
            if login_btn:
                login_btn.click()
            else:
                page.actions.key_down('ENTER').key_up('ENTER')

            time.sleep(10)
            print(f"Итоговый URL: {page.url}")

            error = page.ele('css:.alert-danger', timeout=3)
            if error:
                print(f"Ответ VFS: {error.text}")
                return False
            else:
                print("Вход успешно выполнен.")
                return True
        else:
            print("Поля ввода не найдены.")
            return False

    except Exception as e:
        print(f"Ошибка: {e}")
        return False
    finally:
        page.quit()

def main():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n=== Попытка {attempt} из {MAX_ATTEMPTS} ===")
        if attempt_login():
            print("Программа завершена успешно.")
            sys.exit(0)
        else:
            print(f"Попытка {attempt} провалилась.")
            if attempt < MAX_ATTEMPTS:
                wait_sec = random.randint(5, 15)
                print(f"Ожидание {wait_sec} сек. перед перезапуском...")
                time.sleep(wait_sec)

    print("Все попытки исчерпаны. Вход не выполнен.")
    sys.exit(1)

if __name__ == "__main__":
    main()