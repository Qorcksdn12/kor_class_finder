import pyautogui
import time
import pyperclip
import keyboard
import threading
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 좌표 설정
FIRST_CLICK_X, FIRST_CLICK_Y = 650, 604
NEXT_CLICK_X, NEXT_CLICK_Y = 716, 917
RETRY_BUTTON_X, RETRY_BUTTON_Y = 1240, 892

# 프로그램 종료 여부
stop_flag = False
driver = None

def setup_browser():
    """웹 드라이버 설정"""
    global driver
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_search_results():
    """조회된 발표결과가 있는지 확인"""
    global driver
    
    if driver is None:
        return False  # 드라이버가 없으면 검사 생략
    
    try:
        # 발표결과가 표시되는 테이블 찾기
        # 5초 타임아웃으로 테이블 내용 로딩 대기
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".BD_list table tbody tr"))
        )
        
        # 테이블 행(tr) 요소 찾기
        table_rows = driver.find_elements(By.CSS_SELECTOR, ".BD_list table tbody tr")
        
        # 행이 존재하고 내용이 있는지 확인
        if table_rows and len(table_rows) > 0:
            # 추가 검증: 빈 행이 아닌지 확인
            for row in table_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells and len(cells) > 0:
                    # 적어도 하나의 셀에 내용이 있는지 확인
                    for cell in cells:
                        if cell.text.strip() != "":
                            # 발표결과 발견
                            print("*** 발표결과가 발견되었습니다! ***")
                            print("테이블 내용:")
                            print(row.text)
                            return True
        
        # 결과가 없음
        return False
        
    except TimeoutException:
        # 테이블이 로드되지 않음 (결과 없음)
        return False
    except Exception as e:
        print(f"결과 확인 중 오류 발생: {e}")
        return False

def get_next_date(month, day):
    """다음 날짜 생성 (1월 1일 → 1월 2일 → ... → 12월 31일 후 다시 1월 1일)"""
    day += 1

    # 월별 날짜 제한 체크
    if month in [4, 6, 9, 11] and day > 30:
        day = 1
        month += 1
    elif month == 2 and day > 28:
        day = 1
        month += 1
    elif day > 31:
        day = 1
        month += 1

    if month > 12:
        month = 1
        day = 1

    return month, day

def paste_text(text):
    """클립보드에 텍스트 저장 후 붙여넣기"""
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    
def click_position(x, y):
    """지정된 좌표 클릭"""
    pyautogui.click(x, y)
    time.sleep(0.1)

def detect_f3():
    """F3 키 감지 쓰레드"""
    global stop_flag
    keyboard.wait("f3")
    stop_flag = True
    print("F3 키가 눌려서 프로그램을 종료합니다.")

def load_completed_entries(filename="completed_entries.txt"):
    """완료된 항목 로드"""
    completed = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    name, dates = line.split(":", 1)
                    completed[name] = set(dates.split(","))
    return completed

def save_completed_entry(name, date, filename="completed_entries.txt"):
    """완료된 항목 저장"""
    completed = load_completed_entries(filename)
    
    if name in completed:
        completed[name].add(date)
    else:
        completed[name] = {date}
    
    with open(filename, "w", encoding="utf-8") as f:
        for n, dates in completed.items():
            f.write(f"{n}:{','.join(dates)}\n")

def save_found_result(name, date, result_text, filename="found_results.txt"):
    """발견된 결과 저장"""
    with open(filename, "a", encoding="utf-8") as f:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"=== 발견 시간: {timestamp} ===\n")
        f.write(f"이름: {name}\n")
        f.write(f"생년월일: {date}\n")
        f.write(f"발견된 결과:\n{result_text}\n\n")
    print(f"발견된 결과가 {filename}에 저장되었습니다.")

def take_screenshot(name, date):
    """화면 캡처"""
    if driver:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"result_{name}_{date}_{timestamp}.png"
        driver.save_screenshot(filename)
        print(f"화면 캡처가 {filename}에 저장되었습니다.")

def auto_input():
    global stop_flag, driver
    
    # 사용자 입력
    name = input("이름을 입력하세요: ")
    
    # 셀레니움 초기화
    print("발표결과 확인을 위해 웹 드라이버를 초기화합니다...")
    setup_browser()
    print("웹 드라이버가 초기화되었습니다. 작업할 페이지로 이동해주세요.")
    input("준비가 완료되면 Enter 키를 눌러주세요...")
    
    # 완료된 항목 로드
    completed = load_completed_entries()
    completed_dates = completed.get(name, set())
    
    # 시작 날짜 설정
    start_month = 1
    start_day = 1
    
    # F3 감지 쓰레드 실행
    f3_thread = threading.Thread(target=detect_f3, daemon=True)
    f3_thread.start()
    
    first_run = True
    check_interval = 1  # 매 시도마다 확인
    operation_count = 0
    
    while not stop_flag:
        operation_count += 1
        
        # 날짜 문자열 생성
        date_str = f"09{start_month:02d}{start_day:02d}"
        
        # 이미 처리한 날짜인지 확인
        if date_str in completed_dates:
            print(f"{name}:{date_str} - 이미 처리됨. 다음 날짜로 넘어갑니다.")
            start_month, start_day = get_next_date(start_month, start_day)
            continue
        
        # 클릭 위치 선택
        if first_run:
            click_position(FIRST_CLICK_X, FIRST_CLICK_Y)
            first_run = False
        else:
            click_position(NEXT_CLICK_X, NEXT_CLICK_Y)
        
        # 이름 입력
        paste_text(name)
        time.sleep(0.2)
        pyautogui.press("tab")
        
        # 날짜 입력
        pyautogui.write(date_str)
        pyautogui.press("tab")
        
        # 엔터 누르기
        pyautogui.press("enter")
        time.sleep(0.2)  # 결과 로딩 대기 시간 증가
        
        # 발표결과 확인
        if check_search_results():
            print(f"🎉 축하합니다! {name}:{date_str}에 대한 발표결과가 확인되었습니다.")
            
            # 결과 저장
            if driver:
                result_text = ""
                try:
                    result_element = driver.find_element(By.CSS_SELECTOR, ".BD_list table tbody")
                    result_text = result_element.text
                except:
                    result_text = "결과 텍스트를 가져오지 못했습니다."
                
                # 결과 저장
                save_found_result(name, date_str, result_text)
                
                # 화면 캡처
                take_screenshot(name, date_str)
            
            # 프로그램 정지
            stop_flag = True
            print("발표결과 발견으로 프로그램을 정지합니다.")
            break
        
        # 처리 완료된 항목 저장
        save_completed_entry(name, date_str)
        print(f"{name}:{date_str} - 처리 완료 (결과 없음)")
        
        # 다시조회 버튼 클릭
        click_position(RETRY_BUTTON_X, RETRY_BUTTON_Y)
        time.sleep(0.2)
        
        # 다음 날짜로 업데이트
        start_month, start_day = get_next_date(start_month, start_day)

    # 프로그램 종료
    print("프로그램이 종료되었습니다.")

if __name__ == "__main__":
    try:
        auto_input()
    except Exception as e:
        print(f"오류 발생: {e}")
    finally:
        # 종료 시 브라우저 닫기
        if driver:
            driver.quit()