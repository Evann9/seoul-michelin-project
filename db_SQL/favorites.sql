CREATE TABLE favorites (
    favorites_id INT AUTO_INCREMENT PRIMARY KEY,  -- 1. 고유 번호 (자동 증가)
    restaurant_id INT NOT NULL,                    -- 2. 식당 번호 (비어있으면 안 됨)
    
    -- 3. 외래키 설정 (식당 테이블의 id를 참조)
    CONSTRAINT fk_restaurant_favorite
    FOREIGN KEY (restaurant_id) 
    REFERENCES michelin_star_restaurants (restaurant_id)
    ON DELETE CASCADE                              -- 식당이 삭제되면 즐겨찾기도 같이 삭제!
);