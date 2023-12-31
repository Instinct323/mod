#pragma once

#include <iostream>
#include <fstream>
#include <chrono>

using namespace std;


/**
 * @brief 切换 Windows 命令行编码为 UTF-8
 * @see https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/chcp
 */
void use_utf8() {
    system("chcp 65001");
}


/**
 * @brief 计时器
 */
class Timer {

public:
    Timer() {
        t0 = chrono::steady_clock::now();
    }

protected:
    chrono::steady_clock::time_point t0;

    friend ostream &operator<<(ostream &os, const Timer &obj) {
        chrono::steady_clock::time_point t1 = chrono::steady_clock::now();
        chrono::duration<double> time_used = chrono::duration_cast<chrono::duration<double>>(t1 - obj.t0);
        os << time_used.count();
        return os;
    }
};


/**
 *  @brief 控制对象的存储
 *  @tparam dType - 要序列化/反序列化的数据类型
 */
template<typename dType>
class BinFile {

public:
    /**
     * @param file - 要与 BinFile 对象关联的文件路径
     */
    BinFile(const string file) : file(file) {}

    /**
     *  @brief 序列化函数, 用于将对象序列化并写入文件
     */
    void dump(const dType &obj) {
        fstream f = this->open(ios::out);
        if (f) {
            f << (const char *) &obj;
            f.close();
        }
    }

    /**
     *  @brief 反序列化函数, 用于从文件中读取对象
     */
    void load(dType &obj) {
        fstream f = this->open(ios::in);
        if (f) {
            f.read(reinterpret_cast<char *>(&obj), sizeof(obj));
            f.close();
        }
    }

protected:
    string file;

    fstream open(ios::openmode mode) {
        fstream f(this->file, mode | ios::binary);
        // 检查文件打开状态
        if (!f)
            cerr << "Failed to open file." << endl;
        return f;
    }

    friend ostream &operator<<(ostream &os, const BinFile &obj) {
        os << "BinFile<" << obj.file << ">";
        return os;
    }

};
