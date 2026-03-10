CREATE TABLE reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,   -- 1. 예약 고유 번호 (자동 증가)
    restaurant_id INT NOT NULL,                     -- 2. 어느 식당인지 (FK)
    user_name VARCHAR(50) NOT NULL,                 -- 3. 예약자 이름
    user_phone VARCHAR(20) NOT NULL,                -- 4. 예약자 연락처
    reservation_time INT NOT NULL,                  -- 5. 예약 타임 (1, 2, 3, 4 등)
    
    -- 6. 외래키 설정: 식당 테이블의 ID와 연결
    CONSTRAINT fk_restaurant_reservation
    FOREIGN KEY (restaurant_id) 
    REFERENCES michelin_star_restaurants (restaurant_id)
    ON DELETE CASCADE
);