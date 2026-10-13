# 무료 재고 알림봇

기존 컬리/Hmall 젤다 감시는 2026-10-13 제거했습니다.
아래 네이버 6개 주소를 등록했습니다. **재고 조회 검증이 끝나지 않아 6개 모두 알림이 중지된 상태입니다.**
등록 완료는 실제 재고 감시가 활성화되었다는 뜻이 아닙니다.

- gamewoori: https://smartstore.naver.com/gamewoori/products/13698274396
- nuclearclub: https://smartstore.naver.com/nuclearclub/products/13697333976
- playswitch: https://smartstore.naver.com/playswitch/products/13733754793
- yepanrun: https://smartstore.naver.com/yepanrun/products/13698276158
- bnek: https://smartstore.naver.com/bnek/products/13734519413
- pixeldreams: https://smartstore.naver.com/pixeldreams/products/13699099702

## 검증 상태

겜우리: 클라우드 브라우저에서 로딩 후 ‘상품이 존재하지 않습니다’ 표시.
뉴클리어클럽/플레이스위치: 네이버 보안 인증 화면 표시.
나머지 주소: 네이버 접근 제한으로 실판매 화면 미검증.
GitHub 서버와 클라우드 브라우저는 서로 다른 인증 세션을 사용합니다.
현재 판정기를 활성화하지 않았으며 재고가 존재하거나 품절이라고 가정하지 않습니다.
stock-state.json에서 신규 상품의 재고는 null(미확인)입니다.
로그인 쿠키/비밀번호/인증 토큰을 공개 저장소에 넣지 않습니다. 접근 제한을 우회하지 않습니다.
검증 전에는 네이버 상품에 반복 조회 요청을 보내지 않습니다.

## 무료 운영

공개 저장소의 표준 GitHub Actions 러너, 5분 예약 실행 설정을 유지합니다.
검증 전 예약 실행은 등록/알림 중지 상태만 기록하며 재고 알림을 보내지 않습니다.
실행 지연/누락이 있을 수 있으므로 실시간 알림은 보장하지 않습니다.
유료 서버는 사용하지 않습니다.

## 검사

python -m unittest -v
python monitor.py --dry-run

--test-webhook은 재입고가 아닌 연결 테스트를 전송합니다.
DISCORD_WEBHOOK_URL은 기존 GitHub Actions Secret을 사용합니다.
재고 판정기 검증 후에만 알림을 활성화해야 합니다.
