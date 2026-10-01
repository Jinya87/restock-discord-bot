# 무료 재입고 알림봇

컬리 1002589494 키캡키링만 / 현대Hmall 2253998733 아크릴 스탠드 특전만 감시합니다.
데스크패드는 제외합니다. 자동 구매는 하지 않습니다.

## 무료 운영

공개 저장소의 표준 GitHub Actions 러너로 5분 간격 예약 실행합니다.
실제 실행은 지연/누락될 수 있으며 짧은 재입고를 놓칠 수 있습니다. 실시간 감시는 아닙니다.
비공개 상태에서는 예약 작업을 건너뜁니다. 유료 서버는 사용하지 않습니다.
GitHub는 장기간 활동이 없는 공개 저장소의 예약 워크플로를 비활성화할 수 있으므로 Actions 상태를 주기적으로 확인하세요.

## 연결

Settings → Secrets and variables → Actions → New repository secret.
Name: DISCORD_WEBHOOK_URL. Secret: 본인이 만든 Discord 웹훅을 직접 입력하세요.
웹훅을 코드/채팅에 쓰지 마세요. 저장소가 공개되어도 Secret 값은 공개되지 않습니다.
Actions → Restock Watch → Run workflow에서 test-webhook으로 알림 테스트, dry-run으로 실제 조회만 테스트할 수 있습니다.
테스트 메시지는 재입고를 뜻하지 않습니다. Secret 등록과 공개 전환이 완료되어야 자동 알림을 보냅니다.

## 판정과 한계

컬리 키링 옵션에 가격이 있고 품절/disabled 표시가 없어야 구매 가능입니다.
Hmall은 판매 중단이면 품절. 상품명이 시간의 오카리나+아크릴이고 활성 구매 버튼이 있어야 구매 가능입니다.
Hmall 재판매 시 옵션 구조는 아직 실판매 화면에서 검증하지 못했습니다.
빈 화면/오류/접근 제한은 재입고로 판정하지 않습니다. 사이트 제한은 우회하지 않습니다.
구매 가능이 유지되면 중복 알림을 보내지 않고 품절 후 재입고하면 다시 알립니다.
상태는 stock-state.json에 저장합니다. 상태 저장 실패 시 알림이 중복될 수 있습니다.
2026-10-01 브라우저 확인: 컬리 키링 품절, Hmall 판매 중단.
서버 러너의 사이트 접근과 실제 Discord 전송은 별도 검증이 필요합니다.

## 검사

python -m unittest -v : 판정/오류/중복 방지 10개 검사
python monitor.py --dry-run : 실제 재고 조회만
python monitor.py --test-webhook : Discord 테스트
bot.py와 Dockerfile은 본인 서버가 있을 때 쓰는 선택적 실행 파일입니다. 무료 GitHub 방식에서는 사용하지 않습니다.
render.yaml은 유료 배포를 막기 위해 비활성화했습니다.
