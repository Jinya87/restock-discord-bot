"""Continuous server entrypoint. Interval is between completed checks."""
import os
import subprocess
import sys
import time

def run():
    if not os.environ.get('DISCORD_WEBHOOK_URL'):
        raise SystemExit('DISCORD_WEBHOOK_URL 서버 비밀 환경변수를 등록하세요.')
    interval = max(30, int(os.environ.get('CHECK_INTERVAL_SECONDS', '30')))
    started = subprocess.run([sys.executable, 'monitor.py', '--test-webhook'], check=False)
    if started.returncode:
        raise SystemExit('디스코드 연결 테스트 실패. 감시를 시작하지 않았습니다.')
    print(f'키캡키링 / 아크릴 특전 감시 시작: 조회 완료 후 {interval}초 간격', flush=True)
    while True:
        outcome = subprocess.run([sys.executable, 'monitor.py'], check=False)
        delay = interval if outcome.returncode == 0 else max(interval, 300)
        print(f'다음 조회까지 {delay}초. 오류 시 5분 대기.', flush=True)
        time.sleep(delay)

if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('감시 종료')
