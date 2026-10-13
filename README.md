# 무료 엘든링 재고 알림봇

기존 컬리/Hmall 젤다 감시는 2026-10-13 제거했습니다.
아래 네이버 6개 엘든링 빛바랜 자 에디션 상품을 감시 대상으로 교체했습니다.

- gamewoori: https://smartstore.naver.com/gamewoori/products/13698274396
- nuclearclub: https://smartstore.naver.com/nuclearclub/products/13697333976
- playswitch: https://smartstore.naver.com/playswitch/products/13733754793
- yepanrun: https://smartstore.naver.com/yepanrun/products/13698276158
- bnek: https://smartstore.naver.com/bnek/products/13734519413
- pixeldreams: https://smartstore.naver.com/pixeldreams/products/13699099702

## 재고 판정

요청 URL의 상품 번호와 엘든링 빛바랜 자 상품명을 확인합니다.
상품 제목과 같은 구매 영역의 활성 구매하기 버튼이 두 번 연속 확인되어야 재고가 있다고 판정합니다.
품절 버튼 또는 구매 불가 안내가 우선하며 리뷰/추천 상품 버튼은 판정하지 않습니다.
상품이 존재하지 않는 페이지는 구매 불가 상태로 기록합니다.
보안 인증/접속 오류/불명확한 화면은 미확인으로 기록하며 이전 재고 상태를 유지합니다.
사이트 보안 확인에 막히면 해당 실행에서 같은 호스트의 추가 조회를 중지합니다. 접근 제한은 우회하지 않습니다.
신규 상품의 첫 구매 가능 관측, 또는 구매 불가→구매 가능 전환 때 디스코드 알림을 보냅니다.
구매 가능이 유지되면 중복 알림을 보내지 않습니다.

## 무료 운영과 한계

공개 저장소의 표준 GitHub Actions 러너에서 기존 5분 예약 실행 설정을 유지합니다.
유료 서버는 사용하지 않습니다. 실행 지연/누락이 있을 수 있어 실시간 알림은 보장하지 않습니다.
GitHub 서버와 클라우드 브라우저의 로그인/보안 인증 세션은 서로 다릅니다.
클라우드에서 상품을 읽을 수 있어도 GitHub에서 네이버 인증에 막힐 수 있습니다.
읽지 못한 상태를 재고 있음으로 처리하지 않습니다. Actions의 최신 실행 결과를 확인하세요.
로그인 쿠키/비밀번호/인증 토큰은 공개 저장소에 넣지 않습니다.
재고 표시는 결제 직전에 다시 확인해야 합니다. 자동 구매는 하지 않습니다.

## 2026-10-13 클라우드 확인

겜우리/예판런: 로딩 후 ‘상품이 존재하지 않습니다’ 표시.
뉴클리어클럽/플레이스위치/반다이남코 스토어/픽셀드림즈: 품절되었습니다 표시.
네이버 정상 상품 화면의 구매 영역으로 판정기를 검증했습니다.
GitHub 러너에서의 접근 결과는 Actions 로그가 기준입니다.

## 검사

- python -m unittest -v (13개 오탐/오류/중복 방지 테스트)
- python monitor.py --dry-run (재고 조회, 알림/상태 저장 없음)
- python monitor.py --test-webhook (연결 테스트; 재고 알림 아님)

DISCORD_WEBHOOK_URL은 기존 GitHub Actions Secret을 사용합니다.
