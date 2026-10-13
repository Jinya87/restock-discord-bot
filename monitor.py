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
LABELS = {key: key.split(':')[1] + ' · ' + key.split(':')[2] for key in URLS}
WATCHED = set(URLS)
# Registered URLs are not active until the Naver stock parser and runner access
# are verified. Never infer stock from an authentication/error page.
PENDING_VERIFICATION = set(URLS)
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--test-webhook', action='store_true')
    args = parser.parse_args()
    if args.test_webhook:
        send_discord('✅ 재입고 알림봇 연결 테스트입니다. 네이버 6개 상품이 등록되어 있으며 재고 조회 검증 전까지 알림이 중지되어 있습니다. 이 메시지는 재입고 알림이 아닙니다.')
        print('디스코드 테스트 메시지 전송 완료')
        return 0
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {'stock': {}}
    # Remove retired targets and keep new targets explicitly unknown, not sold out.
    state['stock'] = {key: state.get('stock', {}).get(key) for key in WATCHED}
    current, errors = {}, []
    for key in URLS:
        if key in PENDING_VERIFICATION:
            print(f'{LABELS[key]}: 등록됨 / 재고 미확인 / 알림 중지')
            continue
        # No Naver adapter is enabled before validation against the real page.
        errors.append(key)
        print(f'::error::{LABELS[key]}: 검증된 재고 판정기가 없습니다. 알림을 보내지 않습니다.')
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
