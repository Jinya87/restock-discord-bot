"""Read-only stock checks. Never purchases products or bypasses challenges."""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl
from urllib.request import Request, urlopen
from datetime import datetime, timezone

URLS = {
    'kurly': 'https://www.kurly.com/goods/1002589494?site=market',
    'hmall': 'https://www.hmall.com/md/pda/itemPtc?slitmCd=2253998733',
}
LABELS = {'kurly:desk': '컬리 · 데스크패드', 'kurly:key': '컬리 · 키캡키링', 'hmall': '현대Hmall · 아크릴 스탠드'}
WATCHED = {'kurly:key', 'hmall'}
STATE_FILE = Path(os.environ.get('STATE_FILE', 'stock-state.json'))

def kurly_rows(rows):
    result = {}
    for key, suffix in [('kurly:key', '(키캡키링)')]:
        matches = [r for r in rows if '시간의 오카리나' in r['text'] and suffix in r['text']]
        if len(matches) != 1:
            raise ValueError('컬리 옵션 구조 변경 또는 옵션 누락')
        row = matches[0]
        text = row['text'].strip()
        if '(품절)' in text or row['disabled']:
            result[key] = False
        elif re.search(r'[\d,]+\s*원', text):
            result[key] = True
        else:
            raise ValueError('컬리 가격/옵션 표시 불명확')
    return result

def hmall_status(text, title, buy_enabled):
    if '현재 판매가 중단된 상품' in text:
        return False
    if '시간의 오카리나' not in title or '아크릴' not in title:
        raise ValueError('현대Hmall 상품 확인 실패')
    if '품절' in text and not buy_enabled:
        return False
    if buy_enabled:
        return True
    raise ValueError('현대Hmall 구매 가능 여부 불명확')

def newly_available(previous, current):
    return [key for key, value in current.items() if key in WATCHED and value is True and previous.get(key) is not True]

def send_discord(message):
    secret = os.environ.get('DISCORD_WEBHOOK_URL', '').strip()
    parts = urlsplit(secret)
    if parts.scheme != 'https' or parts.hostname != 'discord.com' or not re.fullmatch(r'/api(?:/v\d+)?/webhooks/\d+/[A-Za-z0-9_-]+', parts.path):
        raise ValueError('DISCORD_WEBHOOK_URL 설정이 없거나 형식이 올바르지 않습니다')
    query = dict(parse_qsl(parts.query)); query['wait'] = 'true'
    endpoint = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ''))
    request = Request(endpoint, data=json.dumps({'content': message, 'allowed_mentions': {'parse': []}}, ensure_ascii=False).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'RestockNotifier/1.0'}, method='POST')
    # Never log the endpoint or raw network exceptions (they can include a token).
    try:
        with urlopen(request, timeout=25) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError('디스코드 전송 실패')
    except Exception:
        raise RuntimeError('디스코드 전송 실패: 웹훅 설정과 Actions 로그 상태를 확인하세요') from None

def check_kurly(page):
    page.get_by_role('heading', level=1).filter(has_text='시간의 오카리나').wait_for(timeout=20000)
    dropdown = page.get_by_role('button', name='상품을 선택해주세요', exact=True)
    dropdown.click(timeout=15000)
    rows = dropdown.locator('..').locator(':scope > ul > li')
    rows.first.wait_for(timeout=10000)
    records = rows.evaluate_all("es => es.map(e => ({text:e.innerText, disabled:!!e.querySelector('[disabled], [aria-disabled=\"true\"]')}))")
    return kurly_rows(records)

def check_hmall(page):
    # Wait for either a known unavailable page or a purchase control; no blind retries.
    page.locator('body').filter(has_text=re.compile('현재 판매가 중단된 상품|품절|구매하기|바로구매|바로 구매')).wait_for(timeout=20000)
    text = page.locator('body').inner_text()
    title = page.title()
    buy_enabled = False
    for role in ['button', 'link']:
        candidates = page.get_by_role(role, name=re.compile(r'^(바로구매|바로 구매|구매하기)$'))
        for button in candidates.all():
            if button.is_visible() and button.is_enabled() and button.get_attribute('aria-disabled') != 'true' and button.get_attribute('disabled') is None:
                buy_enabled = True
    return {'hmall': hmall_status(text, title, buy_enabled)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--test-webhook', action='store_true')
    args = parser.parse_args()
    if args.test_webhook:
        send_discord('✅ 재입고 알림봇 연결 테스트입니다. 컬리 키캡키링 / 현대Hmall 아크릴 특전만 감시합니다. 이 메시지는 재입고 알림이 아닙니다.')
        print('디스코드 테스트 메시지 전송 완료')
        return 0
    from playwright.sync_api import sync_playwright
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {'stock': {}}
    current, errors = {}, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(locale='ko-KR')
        for shop, url in URLS.items():
            page = context.new_page()
            try:
                response = page.goto(url, wait_until='domcontentloaded', timeout=35000)
                if response is None or response.status >= 400:
                    raise ValueError('상품 페이지 접근 실패')
                text = page.locator('body').inner_text(timeout=10000).lower()
                if any(marker in text for marker in ['verify you are human', 'checking your browser', 'access denied', '로봇이 아닙니다']):
                    raise ValueError('사이트 접근 확인 필요: 자동 우회하지 않습니다')
                observation = check_kurly(page) if shop == 'kurly' else check_hmall(page)
                current.update(observation)
                print(shop, json.dumps(observation, ensure_ascii=False))
            except Exception as exc:
                # Shop network errors never become an in-stock observation.
                errors.append(shop)
                print(f'::error::{shop} 재고 조회 실패 ({type(exc).__name__}). 이전 재고 상태 유지.')
            finally:
                page.close()
        browser.close()
    if not args.dry_run:
        old = state.get('stock', {})
        for key in newly_available(old, current):
            shop = key.split(':')[0]
            send_discord(f'🔔 구매 가능 상태 감지\n젤다의 전설 시간의 오카리나\n{LABELS[key]}\n{URLS[shop]}\n결제 전 옵션과 재고를 직접 확인하세요.')
            # Save immediately after confirmed delivery; failures remain retryable.
            old[key] = True
            state['stock'] = old
            STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        old.update(current)
        state['stock'] = old
        state['last_check_utc'] = datetime.now(timezone.utc).isoformat()
        state['failed_shops'] = errors
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as output:
            output.write('## 재고 조회 결과\n\n')
            for key, value in current.items():
                output.write(f'- {LABELS[key]}: {"구매 가능" if value else "품절/판매 중단"}\n')
            for shop in errors:
                output.write(f'- {shop}: **조회 실패 — 재고 미확인**\n')
            if args.dry_run:
                output.write('\n조회 테스트: 디스코드 전송과 상태 저장을 하지 않았습니다.\n')
    return 1 if errors else 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'::error::실행 중단 ({type(exc).__name__}). 웹훅 설정 또는 상태 파일을 확인하세요.')
        sys.exit(1)
