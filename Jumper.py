import cv2
import numpy as np
from PIL import ImageGrab
import win32api, win32con
import random

def click(x,y, t):
    win32api.SetCursorPos((x,y))                                        # 移动鼠标位置
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)     # 发出按下左键指令
    cv2.waitKey(np.int(t*1000))                                         # 等待我们计算好的延迟时间 *1000 是换算成毫秒
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)           # 发出释放左键指令
    return


def draw_loc(imgin, loc, color = (0, 0, 255)):
    loc = np.uint16(np.around(loc))
    cv2.putText(imgin, '(' + str(loc[0]) + ',' + str(loc[1]) + ")", (loc[0] + 30, loc[1] +30), cv2.FONT_HERSHEY_PLAIN ,
                2, color, 2)
    return


def draw_text(imgin, loc, text):
    loc = np.uint16(np.around(loc))
    cv2.putText(imgin, text, (loc[0] + 10, loc[1] +30), cv2.FONT_HERSHEY_PLAIN ,
                2, (255, 125, 127), 2)
    return


def find_head(img, output_img):
    # find small circles
    head_found = False
    trial_cnt = 0
    while(head_found == False):
        #processing img
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel)
        edges = cv2.Canny(closed, 200, 200)             # use full colour img for canny
        circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, 2, 180 - trial_cnt *10,
                                   param1=100, param2=65, minRadius=12, maxRadius=18)
        gray = cv2.cvtColor(closed, cv2.COLOR_RGB2GRAY)

        # if nothing found, will return None, then try a few time.
        if(circles is not None):
            head_found = True
        else:
            if (trial_cnt > 5):     # return 0 as error.
                return 0, 0, 0
        trial_cnt += 1

    circles = np.uint16(np.around(circles))

    # circle to return
    xo=0
    yo=0
    ro=0

    # find and draw  # 遍历所有找到的
    for i in circles[0, :]:
        x = i[0]
        y = i[1]
        r = i[2]

        # find the head
        if (r < 25 and y > 380 and y < 520 ):
            # 画出来
            cv2.circle(output_img, (i[0], i[1]), i[2], (128, 0, 255), 2)  # outer
            cv2.circle(output_img, (i[0], i[1]), 2, (128, 0, 255), 3)  # centre

            if((y < yo or yo is  0 )): # 寻找位置最靠上的那个源（有时候身子也会被识别成圆）
                xo=x
                yo=y
                ro=r
        # not the head #
        else:
            # 不是头，用另一种颜色画出来
            cv2.circle(output_img, (i[0], i[1]), i[2], (127, 127, 0), 2)
            cv2.circle(output_img, (i[0], i[1]), 2, (127, 127, 0), 3)

    # 判断头位置的辅助线
    cv2.line(output_img, (0, 380), (540, 380), (128, 0, 255), 1)
    cv2.line(output_img, (0, 530), (540, 530), (128, 0, 255), 1)

   # cv2.imshow("Head", edges)
    return xo, yo, ro


def find_foot_loc(x,y,r):
    xo = x
    yo = y + 75 # distance between head to foot
    return (xo, yo)


def find_target_loc(img, output_img, loc_foot, index = 0):
    edges = cv2.Canny(img, 15, 70)
    points = cv2.findNonZero(edges)   # find all none zero point
    #print(points)
    for point in points:
        x = point[0][0]
        y = point[0][1]

        if y < 250:
            continue
        if np.abs(x - loc_foot[0]) < 30: # horizontal distance to foot
            continue
        if loc_foot[1] - y < 30:   # higher than foot
            continue
        if x < 50 or x > 540 - 50: # too close to bondary
            continue
        break

    # Find top tips of the target
    xo = x              # 0~33步 是大图形，偏移量比较多
    yo = y + 45

    if index > 33:      # 33步~75步 是中等图形， 偏移量减小
        yo = y + 35
    if index > 75:      # 75 步以上 都是非常小的图形比较多， 偏移量最小
        yo = y + 20

    cv2.imshow('Canny Line', edges)
    return (xo, yo)


if __name__ == "__main__":

    step = 0            # 现在是第几步
    fault = 0           # 距离上一次成功的时候，尝试了几次了
    fault_cnt = 0       # 一共错了几次
    while(1):

        # 第几步？
        step = step + 1

        # 截取屏幕
        file_name = 'temp.bmp'
        im = ImageGrab.grab(bbox=(0, 70, 558, 1045))  # 魔法参数1
        im.save(file_name,'bmp')
        img = cv2.imread(file_name)
        img = cv2.resize(img, (540, 960))             # 统一转换成 540*960 分辨率
        output_img = img.copy()                       # 复制一张图用来输出
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)  # 生成驿站灰图备用

        # find (and draw) head, and foot location
        i = find_head(img, output_img)                      # 找小人的头
        if(i[2] == 0):                                      # 如果没找到，延迟500ms重新截图再找
            cv2.waitKey(500)
            fault += 1
            if(fault < 3):    # try a few time before letting it go thought. code will exit later
                continue      #

        # find foot location according to head location
        loc_foot = find_foot_loc(i[0],i[1],i[2])            # 找到小人脚部的位置

        # find (and draw) target
        loc_target = find_target_loc(img, output_img, loc_foot, step)  # 找落点

        # calculate distance
        dist = np.sqrt((loc_target[0] - loc_foot[0])*(loc_target[0] - loc_foot[0])      # 三角函数咯，计算距离
                       + (loc_target[1] - loc_foot[1])*(loc_target[1] - loc_foot[1]))

        # calculate pressing time
        time = dist / 365               # 魔法参数2
        #time = dist / 385 + 0.03
        #time = dist / 375 + 0.01


        # -------- Draw informations on output image ---------------
        # me and target
        cv2.circle(output_img, loc_foot, 3, (255,0,255), 3)         # foot
        draw_loc(output_img, loc_foot, (255,0,0))                   #
        cv2.circle(output_img, loc_target, 3, (255, 0, 255), 3)     # target
        draw_loc(output_img, loc_target, (255,0,0))

        # draw line between me and target
        cv2.line(output_img, loc_foot, loc_target, (255,0,0), 3)    # 小人位置跟目标落点之间画一条线

        # print information on output image
        draw_text(output_img, (50, 200), 'Distance  :' + str(np.int(dist)) + 'pix')    # 距离
        draw_text(output_img, (50, 250), 'Press time:' + str(np.int(time*1000)) + 'ms')# 时间
        draw_text(output_img, (50, 300), 'Faults     :' + str(fault_cnt))              # 错误次数

        # print step
        cv2.putText(output_img, 'STEP:'+ str(step), (50,50), cv2.FONT_HERSHEY_SIMPLEX, # 第几步了
                    1, (255, 0, 225), 2)

       #cv2.imshow("gray", gray)
        cv2.imshow('OUTPUT', output_img)


        # ------- validate parameters before pressing the screen ------------
        # check if the screen is error screen, restart needed
        brightness = gray[10, 10]       # 取像素位置x:10 y:10 的亮度，判断是否跳出了失败界面
        if brightness < 50:             # 正常亮度为90， 天黑时最低为54，失败界面30+
            step = 0
            fault = 0
            fault_cnt = 0
            cv2.waitKey(2000)
            click(288, 880, 0.015)     # 点一下重新开始
            #continue

        #check if valid                # 检测一下小人和目标之间的距离，太大或者太小都不行
        if(dist < 50 or dist > 700):
            fault = fault + 1          # will be reset
            fault_cnt = fault_cnt+1    # not not be reset
            cv2.waitKey(2000)
            if fault > 10:
                exit()
            continue

        # if everything is checked and we are ready to jump!
        fault = 0
        cv2.waitKey(100)                                # 稍微等一下，留时间给 opencv 绘图并输出 output image
        click_x = 288 + random.randint(-60, 60)         # 防作弊，变换点击位置
        click_y = 880 + random.randint(-20, 20)
        click(click_x, click_y, time)
        cv2.waitKey(2000 + random.randint(-100, 300))   # 防作弊，随机等待时间
