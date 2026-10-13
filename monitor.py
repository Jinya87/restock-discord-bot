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
    "naver:gamewoori:13698274396": "https://smartstore.naver.com/gamewoori/products/13698274396",
    "naver:nuclearclub:13697333976": "https://smartstore.naver.com/nuclearclub/products/13697333976",
    "naver:playswitch:13733754793": "https://smartstore.naver.com/playswitch/products/13733754793",
    "naver:yepanrun:13698276158": "https://smartstore.naver.com/yepanrun/products/13698276158",
    "naver:bnek:13734519413": "https://smartstore.naver.com/bnek/products/13734519413",
    "naver:pixeldreams:13699099702": "https://smartstore.naver.com/pixeldreams/products/13699099702"
}
STORES = {'gamewoori': '겜우리', 'nuclearclub': '뉴클리어클럽', 'playswitch': '플레이스위치', 'yepanrun': '예판런', 'bnek': '반다이남코 스토어', 'pixeldreams': '픽셀드림즈'}
LABELS = {key: STORES[key.split(':')[1]] + ' · 엘든링 빛바랜 자 에디션' for key in URLS}
WATCHED = set(URLS)
# Never infer stock from authentication, network errors, or unrelated reviews.
PENDING_VERIFICATION = set()
STATE_FILE = Path(os.environ.get('STATE_FILE', 'stock-state.json'))

def newly_available(previous, current):
    return [key for key, value in current.items() if key in WATCHED and key not in PENDING_VERIFICATION and value is True and previous.get(key) is not True]

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


def naver_status(key, page_url, title, panel_text, controls):
    expected = urlsplit(URLS[key])
    actual = urlsplit(page_url)
    if actual.hostname not in {'smartstore.naver.com', 'm.smartstore.naver.com'} or actual.path != expected.path:
        raise ValueError('요청 상품 주소 불일치')
    lower = panel_text.lower()
    if any(marker in lower for marker in ['security verification', 'verify you are human', 'captcha', '현재 서비스 접속이 불가']):
        raise ValueError('접근 제한 또는 접속 오류: 재고 미확인')
    if '상품이 존재하지 않습니다' in panel_text:
        return False
    compact_title = re.sub(r'\s+', '', title).lower()
    if not ('엘든링' in compact_title or 'eldenring' in compact_title) or '빛바랜' not in title:
        raise ValueError('엘든링 빛바랜 자 상품 확인 실패')
    shown = [item for item in controls if item.get('visible')]
    if any('품절' in item['text'] or '판매중지' in item['text'] for item in shown) or '현재 구매하실 수 없는 상품' in panel_text:
        return False
    buyers = [item for item in shown if re.fullmatch(r'(?:N)?구매하기', re.sub(r'\s+', '', item['text']))]
    if buyers and all(item.get('enabled') for item in buyers):
        return True
    raise ValueError('구매 영역 재고 표시 불명확')

def naver_snapshot(page, key):
    text = page.locator('body').inner_text(timeout=5000)
    if '상품이 존재하지 않습니다' in text:
        return naver_status(key, page.url, '', '상품이 존재하지 않습니다', [])
    if any(marker in text.lower() for marker in ['security verification', 'verify you are human', 'captcha', '현재 서비스 접속이 불가']):
        raise ValueError('네이버 접근 확인 필요')
    heading = page.get_by_role('heading', level=3).filter(has_text=re.compile(r'엘든\s*링|ELDEN\s*RING', re.I))
    if heading.count() != 1:
        raise ValueError('상품 제목 누락/중복')
    # The purchase panel is two ancestors above the primary product heading.
    # Do not read review/recommendation buttons as a stock signal.
    data = heading.evaluate("""h => {
        const panel = h.parentElement.parentElement;
        return {title: h.innerText, text: panel.innerText,
          controls: [...panel.querySelectorAll('button,a')].map(e => ({
            text: e.innerText.trim(),
            visible: !!(e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden'),
            enabled: !e.matches('[disabled],[aria-disabled="true"]')
              && !e.closest('[aria-disabled="true"]')
          }))};
    }""")
    return naver_status(key, page.url, data['title'], data['text'], data['controls'])

def check_naver(page, key):
    page.wait_for_load_state('load', timeout=15000)
    # Allow normal rendering and automatic site verification to complete.
    page.wait_for_timeout(3000)
    page.get_by_text('Verifying ...', exact=True).wait_for(state='hidden', timeout=15000)
    page.locator('body').filter(has_text=re.compile(r'상품이 존재하지 않습니다|품절되었습니다|현재 구매하실 수 없는 상품|구매하기|현재 서비스 접속이 불가|security verification|captcha', re.I)).wait_for(timeout=15000)
    first = naver_snapshot(page, key)
    page.wait_for_timeout(3000)
    second = naver_snapshot(page, key)
    if first != second:
        raise ValueError('로딩 중 재고 표시 변경: 알림 보류')
    return second


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--test-webhook', action='store_true')
    args = parser.parse_args()
    if args.test_webhook:
        send_discord('✅ 재입고 알림봇 연결 테스트입니다. 네이버 6개 엘든링 상품을 감시합니다. 이 메시지는 재입고 알림이 아닙니다.')
        print('디스코드 테스트 메시지 전송 완료')
        return 0
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {'stock': {}}
    # Remove retired targets and keep new targets explicitly unknown, not sold out.
    state['stock'] = {key: state.get('stock', {}).get(key) for key in WATCHED}
    current, errors = {}, []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(locale='ko-KR')
        host_blocked = False
        for key, url in URLS.items():
            if host_blocked:
                errors.append(key)
                print(f'::warning::{LABELS[key]}: 네이버 접근 제한으로 같은 호스트 추가 조회 중지.')
                continue
            page = context.new_page()
            try:
                response = page.goto(url, wait_until='domcontentloaded', timeout=20000)
                if response is None or response.status >= 400:
                    raise ValueError('상품 페이지 응답 오류 HTTP ' + str(response.status if response else 'none'))
                current[key] = check_naver(page, key)
                print(LABELS[key], json.dumps({'stock': current[key]}, ensure_ascii=False))
            except Exception as exc:
                errors.append(key)
                reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                print(f'::warning::{LABELS[key]}: 조회 실패/재고 미확인 ({reason}). 이전 상태 유지, 알림 없음.')
                try:
                    text = page.locator('body').inner_text(timeout=3000).lower()
                    host_blocked = any(marker in text for marker in ['security verification', 'verify you are human', 'captcha', '비정상적인 접근', '접근이 제한'])
                except Exception:
                    pass
            finally:
                page.close()
        browser.close()
    if not args.dry_run:
        old = state.get('stock', {})
        for key in newly_available(old, current):
            send_discord(f'🔔 구매 가능 상태 감지\n{LABELS[key]}\n{URLS[key]}\n결제 전 옵션과 재고를 직접 확인하세요.')
            # Save immediately after confirmed delivery; failures remain retryable.
            old[key] = True
            state['stock'] = old
            STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        old.update(current)
        state['stock'] = old
        state['last_check_utc'] = datetime.now(timezone.utc).isoformat()
        state['failed_shops'] = errors
        state['pending_verification'] = sorted(PENDING_VERIFICATION)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as output:
            output.write('## 재고 조회 결과\n\n')
            for key in sorted(PENDING_VERIFICATION):
                output.write(f'- {LABELS[key]}: **등록됨 · 재고 미확인 · 알림 중지**\n')
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
