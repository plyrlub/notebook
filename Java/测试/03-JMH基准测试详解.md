---
tags: [JMH, 基准测试, 性能测试, 微基准, Java]
创建日期: 2026-08-09
状态: ✅ 已归档（01-学习/Java/测试）
归属: 01-学习/Java/测试
---

# 03-JMH基准测试详解

> 版本基线：JMH（Java Microbenchmark Harness），Oracle 官方微基准测试工具
> 受众：Java 后端开发，要写可靠的性能微基准测试（避免 JIT 优化误导）。默认你懂 Maven、JUnit（[01-JUnit 5详解](01-JUnit 5详解.md)）。
> 关联笔记：[00-测试体系总览](00-测试体系总览.md)、[01-JUnit 5详解](01-JUnit 5详解.md)

## 📋 总纲

- 1. 基础
- 2. 高级
- 3. JMH 的 Profiler

## 学习目标

学完本篇你能：

1. 理解 JMH 为什么重要（对抗 JIT 优化的微基准）
2. 用 @Benchmark/@State/@Param 等注解写基准测试
3. 配置 Warmup/Measurement/BenchmarkMode/OutputTimeUnit
4. 避免 DCE/常量折叠等正确性陷阱
5. 用 Blackhole/Fork 保证测试有效
6. 用 Profiler 分析栈/GC/编译

## 前置知识

- [01-JUnit 5详解](01-JUnit 5详解.md)——测试基础
- 需掌握：Java 注解、JIT 基本概念

---

```java
@BenchmarkMode(Mode.AverageTime)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
@State(Scope.Thread)
public class Test001 {

    private static final String DATA = "Dummy Data";
    private List<String> arrList;
    private List<String> linkList;

    @Setup(Level.Iteration)
    public void setup(){
        this.arrList = new ArrayList<>();
        this.linkList = new LinkedList<>();
    }

    @Benchmark
    public List<String> arrListAdd(){
        this.arrList.add(DATA);
        return arrList;
    }

    @Benchmark
    public List<String> linkListAdd(){
        this.linkList.add(DATA);
        return linkList;
    }

    public static void main(String[] args) throws RunnerException {

        Options options = new OptionsBuilder().include(Test001.class.getSimpleName())
                .forks(1)
                .measurementIterations(5)
                .warmupIterations(3)
                .build();

        new Runner(options).run();

    }
}
```
# 基础
## @Benchmark
标记基准测试方法
JMH对基准测试的方法需要使用@Benchmark注解进行标记，否则方法将被视为普通方法，并且不会对其执行基准测试。
> [!note]
> 如果一个类中没有任何基准测试方法（被@Benchmark标记的方法），那么对其进行基准测试则会出现异常。
> Exception in thread "main" No benchmarks to run; check the include/exclude regexps.
## Warmup
在JMH中，Warmup所做的就是在基准测试代码正式度量之前，先对其进行预热，使得代码的执行是经历过了类的早期优化、JVM运行期编译、JIT优化之后的最终状态，从而能够获得代码真实的性能数据。
### 设置全局预热
1. Options构建设置
  如上面的例子中设置预热的方式
1. 注解设置
```java
@Warmup(iterations = 3)
public class Test001 {}
```
### 方法上设置
```java
@Warmup(iterations = 3)
public List<String> arrListAdd(){}
```
## Measurement
在JMH中，Warmup所做的就是在基准测试代码正式度量之前，先对其进行预热，使得代码的执行是经历过了类的早期优化、JVM运行期编译、JIT优化之后的最终状态，从而能够获得代码真实的性能数据。
### 设置全局度量
1. Options构建设置
  如上面的例子中设置预热的方式
1. 注解设置
```java
@Measurement(iterations =10)
public class Test001 {}
```
### 方法上设置
```java
@Measurement(iterations = 3)
public List<String> arrListAdd(){}
```
## 基本测试结果说明
```bash
# JMH version: 1.35
# VM version: JDK 11.0.10, Java HotSpot(TM) 64-Bit Server VM, 11.0.10+8-LTS-162
# VM invoker: /Library/Java/JavaVirtualMachines/jdk-11.0.10.jdk/Contents/Home/bin/java
# VM options: -Xms4g -Xmx4g -Dfile.encoding=UTF-8
# Blackhole mode: full + dont-inline hint (auto-detected, use -Djmh.blackhole.autoDetect=false to disable)
# 预热 3 次，每轮执行 10s
# Warmup: 3 iterations, 10 s each
# 度量测试 5 轮
# Measurement: 5 iterations, 10 s each
# 每个批次的超时时间
# Timeout: 10 min per iteration
# 执行基准测试线程数量
# Threads: 1 thread, will synchronize iterations
# 模式，这里表示耗时均值
# Benchmark mode: Average time, time/op
# 测试方法全类名
# Benchmark: org.lub.demo001.Test001.linkListAdd

# 执行进度
# Run progress: 50.00% complete, ETA 00:00:40
# Fork: 1 of 1
# 预热执行，耗时均值
# Warmup Iteration   1: 0.270 us/op
# Warmup Iteration   2: 0.310 us/op
# Warmup Iteration   3: 0.365 us/op
# 度量执行，耗时均值
Iteration   1: 0.353 us/op
Iteration   2: 0.324 us/op
Iteration   3: 0.280 us/op
Iteration   4: 0.331 us/op
Iteration   5: 0.315 us/op

Result "org.lub.demo001.Test001.linkListAdd":
  0.321 ±(99.9%) 0.104 us/op [Average]
  # 最小，平均，最大，标准误差
  (min, avg, max) = (0.280, 0.321, 0.353), stdev = 0.027
  CI (99.9%): [0.217, 0.424] (assumes normal distribution)

# Run complete. Total time: 00:02:14

REMEMBER: The numbers below are just data. To gain reusable insights, you need to follow up on
why the numbers are the way they are. Use profilers (see -prof, -lprof), design factorial
experiments, perform baseline and negative tests that provide experimental control, make sure
the benchmarking environment is safe on JVM/OS/HW level, ask for reviews from the domain experts.
Do not assume the numbers tell you what you want them to tell.

Benchmark            Mode  Cnt  Score   Error  Units
Test001.linkListAdd  avgt    5  0.321 ± 0.104  us/op
```
## BenchmarkMode
JMH为我们提供了四种运行模式，当然它还允许若干个模式同时存在
### AverageTime
平均响应时间
主要用于输出基准测试方法每调用一次所耗费的时间，也就是elapsed time/operation。
### Throughput
方法吞吐量
它的输出信息表明了在单位时间内可以对该方法调用多少次
```java
@BenchmarkMode(Mode.Throughput)
@Benchmark
public static void test001() throws InterruptedException {
    TimeUnit.SECONDS.sleep(1);
}
```
```bash
# Run progress: 0.00% complete, ETA 00:01:20
# Fork: 1 of 1
# Warmup Iteration   1: 0.997 ops/s
# Warmup Iteration   2: 0.997 ops/s
# Warmup Iteration   3: 0.996 ops/s
Iteration   1: 0.997 ops/s
Iteration   2: 0.997 ops/s
Iteration   3: 0.997 ops/s
Iteration   4: 0.997 ops/s
Iteration   5: 0.996 ops/s

Result "org.lub.demo001.Test002.test001":
  0.997 ±(99.9%) 0.002 ops/s [Average]
  (min, avg, max) = (0.996, 0.997, 0.997), stdev = 0.001
  CI (99.9%): [0.995, 0.999] (assumes normal distribution)

# Run complete. Total time: 00:01:32

Benchmark         Mode  Cnt  Score   Error  Units
Test002.test001  thrpt    5  0.997 ± 0.002  ops/s
```
### SampleTime
时间采样
指采用一种抽样的方式来统计基准测试方法的性能结果，与我们常见的Histogram图（直方图）几乎是一样的，它会收集所有的性能数据，并且将其分布在不同的区间中。
```java
@BenchmarkMode(Mode.SampleTime)
@Benchmark
public static void test001() throws InterruptedException {
    TimeUnit.SECONDS.sleep(1);
}
```
```bash
Result "org.lub.demo001.Test002.test001":
  N = 50
  mean =      1.002 ±(99.9%) 0.001 s/op

  Histogram, s/op:
    [0.999, 0.999) = 5
    [0.999, 1.000) = 0
    [1.000, 1.001) = 7
    [1.001, 1.001) = 0
    [1.001, 1.002) = 6
    [1.002, 1.002) = 0
    [1.002, 1.003) = 11
    [1.003, 1.003) = 0
    [1.003, 1.004) = 11
    [1.004, 1.004) = 0
    [1.004, 1.005) = 0
    [1.005, 1.005) = 10

  Percentiles, s/op:
      p(0.0000) =      0.999 s/op
     p(50.0000) =      1.002 s/op
     p(90.0000) =      1.005 s/op
     p(95.0000) =      1.005 s/op
     p(99.0000) =      1.005 s/op
     p(99.9000) =      1.005 s/op
     p(99.9900) =      1.005 s/op
     p(99.9990) =      1.005 s/op
     p(99.9999) =      1.005 s/op
    p(100.0000) =      1.005 s/op

# Run complete. Total time: 00:01:29

Benchmark                          Mode  Cnt  Score   Error  Units
Test002.test001                  sample   50  1.002 ± 0.001   s/op
Test002.test001:test001·p0.00    sample       0.999           s/op
Test002.test001:test001·p0.50    sample       1.002           s/op
Test002.test001:test001·p0.90    sample       1.005           s/op
Test002.test001:test001·p0.95    sample       1.005           s/op
Test002.test001:test001·p0.99    sample       1.005           s/op
Test002.test001:test001·p0.999   sample       1.005           s/op
Test002.test001:test001·p0.9999  sample       1.005           s/op
Test002.test001:test001·p1.00    sample       1.005           s/op
```
### SingleShotTime
可用来进行冷测试，不论是Warmup还是Measurement，在每一个批次中基准测试方法只会被执行一次，
一般情况下，我们会将Warmup的批次设置为0
```java
@BenchmarkMode(Mode.SingleShotTime)
@Benchmark
@Warmup(iterations = 0)
public static void test001() throws InterruptedException {
    TimeUnit.SECONDS.sleep(1);
}
```
```bash
Result "org.lub.demo001.Test002.test001":
  N = 5
  mean =      1.003 ±(99.9%) 0.006 s/op

  Histogram, s/op:
    [1.001, 1.001) = 1
    [1.001, 1.002) = 0
    [1.002, 1.002) = 0
    [1.002, 1.002) = 0
    [1.002, 1.002) = 0
    [1.002, 1.003) = 1
    [1.003, 1.003) = 0
    [1.003, 1.003) = 0
    [1.003, 1.003) = 0
    [1.003, 1.004) = 0
    [1.004, 1.004) = 1
    [1.004, 1.004) = 0
    [1.004, 1.004) = 0
    [1.004, 1.005) = 0
    [1.005, 1.005) = 0
    [1.005, 1.005) = 1
    [1.005, 1.005) = 1
    [1.005, 1.006) = 0
    [1.006, 1.006) = 0

  Percentiles, s/op:
      p(0.0000) =      1.001 s/op
     p(50.0000) =      1.004 s/op
     p(90.0000) =      1.005 s/op
     p(95.0000) =      1.005 s/op
     p(99.0000) =      1.005 s/op
     p(99.9000) =      1.005 s/op
     p(99.9900) =      1.005 s/op
     p(99.9990) =      1.005 s/op
     p(99.9999) =      1.005 s/op
    p(100.0000) =      1.005 s/op

# Run complete. Total time: 00:00:15

Benchmark        Mode  Cnt  Score   Error  Units
Test002.test001    ss    5  1.003 ± 0.006   s/op
```
### 多Mode
除了对某个基准测试方法设置上述四个模式中的一个之外，还可以为其设置多个模式的方式运行基准测试方法，
如果愿意，甚至可以设置全部的Mode。
```java
@BenchmarkMode(Mode.All)
@Benchmark
public static void test001() throws InterruptedException {
    TimeUnit.SECONDS.sleep(1);
}
```
> [!note]
> BenchmarkMode既可以在class上进行注解设置，也可以在基准方法上进行注解设置，方法中设置的模式将会覆盖class注解上的设置，同样，在Options中也可以进行设置，它将会覆盖所有基准方法上的设置。
## OutputTimeUnit
OutputTimeUnit提供了统计结果输出时的单位，
比如，调用一次该方法将会耗费多少个单位时间，或者在单位时间内对该方法进行了多少次的调用，
同样，OutputTimeUnit既可以设置在class上，也可以设置在method上，还可以在Options中进行设置，它们的覆盖次序与BenchmarkMode一致
```java
@OutputTimeUnit(TimeUnit.NANOSECONDS)
```
## 三大 State
在JMH中，有三大State分别对应于Scope的三个枚举值。
- Benchmark
- Thread
- Group
### Thread独享的State
所谓线程独享的State是指，每一个运行基准测试方法的线程都会持有一个独立的对象实例，
该实例既可能是作为基准测试方法参数传入的，也可能是运行基准方法所在的宿主class，
将State设置为Scope.Thread一般主要是针对非线程安全的类。
```java
@BenchmarkMode(Mode.AverageTime)
@Fork(1)
@Warmup(iterations = 3)
@Measurement(iterations = 5)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
// 设置 5 个线程运行基准测试方法
@Threads(5)
public class Test003 {
    // 每个线程都有 Test 对象
    @State(Scope.Thread)
    public static class Test{
        public Test() {
            System.out.println("---");
        }
        public void run() {}
    }

    @Benchmark
    public void test01(Test t1){
        t1.run();
    }

    public static void main(String[] args) throws RunnerException {
        Options options = new OptionsBuilder()
                .include(Test003.class.getSimpleName())
                .build();

        new Runner(options).run();
    }
}
```
```bash
# Warmup Iteration   1:
---
---
---
---
---
0.001 ±(99.9%) 0.001 us/op
```
### Thread共享的State
需要测试在多线程的情况下某个类被不同线程操作时的性能，
比如，多线程访问某个共享数据时，我们需要让多个线程使用同一个实例才可以。
因此JMH提供了多线程共享的一种状态Scope.Benchmark
```java
// 还是上面的案例，只是修改的地方单独拿出来
@State(Scope.Benchmark)
public static class Test{
    public Test() {
        System.out.println("---");
    }
    public void run() {}
}
```
```bash
# Run progress: 0.00% complete, ETA 00:01:20
# Fork: 1 of 1
# Warmup Iteration   1:
---
0.001 ±(99.9%) 0.001 us/op
```
### 线程组共享的State
截至目前，我们所编写的基准测试方法都会被JMH框架根据方法名的字典顺序排序后按照顺序逐个地调用执行，因此不存在两个方法同时运行的情况，如果想要测试某个共享数据或共享资源在多线程的情况下同时被读写的行为，是没有办法进行的，比如，在多线程高并发的环境中，多个线程同时对一个ConcurrentHashMap进行读写。
第一，是在多线程情况下的单个实例；
第二，允许一个以上的基准测试方法并发并行地运行。
```java
@BenchmarkMode(Mode.AverageTime)
@Fork(1)
@Warmup(iterations =3)
@Measurement(iterations = 5)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
public class Test004 {

    // 将 Test 设置为线程组共享
    @State(Scope.Group)
    public static class Test{
        public Test(){
            System.out.println("create instance ...");
        }
        public void write(){
            System.out.println("w");
        }
        public void read(){
            System.out.println('r');
        }

    }
    // 在线程组test中，有三个线程将不断地对 Test 实例的write方法进行调用
    @GroupThreads(3)
    @Group("test")
    @Benchmark
    public void testW(Test t){
        t.write();
    }

    // 在线程组test中，有三个线程将不断地对 Test 实例的read方法进行调用
    @GroupThreads(3)
    @Group("test")
    @Benchmark
    public void testR(Test t){
        t.read();
    }

    public static void main(String[] args) throws RunnerException {
        Options options = new OptionsBuilder()
                .include(Test004.class.getSimpleName())
                .build();

        new Runner(options).run();
    }

}
```
```bash
# Warmup: 3 iterations, 10 s each
# Measurement: 5 iterations, 10 s each
# Timeout: 10 min per iteration
总共6 个线程，
# Threads: 6 threads (1 group; 3x "testR", 3x "testW" in each group), will synchronize iterations
# Benchmark mode: Average time, time/op
# Benchmark: org.lub.demo001.Test004.test

...
交替运行
r
r
w
w
r
r
r
...
```
## @Param
使得参数可配置，也就是说一个参数在每一次的基准测试时都会有不同的值与之对应。
```java
@BenchmarkMode(Mode.AverageTime)
@Fork(1)
@Warmup(iterations = 3)
@Measurement(iterations = 5)
@OutputTimeUnit(TimeUnit.MICROSECONDS)
// 5 个线程同时对共享资源操作
@Threads(5)
// 多个线程使用同一实例
@State(Scope.Benchmark)
public class Test005 {
    @Param({"1", "2", "3", "4", "5"})
    private int type;

    private Map<Long, Long> map;

    @Setup
    public void setup() {
        switch (type) {
            case 1:
                this.map = new ConcurrentHashMap<>();
                break;
            case 2:
                this.map = new ConcurrentSkipListMap<>();
                break;
            case 3:
                this.map = new Hashtable<>();
                break;
            case 4:
                this.map = Collections.synchronizedMap(new HashMap<>());
                break;
            default:
                throw new IllegalArgumentException("...");
        }
    }

    @Benchmark
    public void test() {
        this.map.put(System.nanoTime(), System.nanoTime());
    }

    public static void main(String[] args) throws RunnerException {
        Options options = new OptionsBuilder()
                .include(Test005.class.getSimpleName())
                .build();

        new Runner(options).run();
    }

}
```
由于引进了@Param对变量的可配置化
因此只需要写一个基准测试方法即可，JMH会根据@Param所提供的参数值，对test方法分别进行基准测试的运行与统计
这样就不需要为每一个map容器都写一个基准测试方法了。
```bash
Benchmark     (type)  Mode  Cnt  Score     Error  Units
Test005.test       1  avgt    3  5.658 ±  58.730  us/op
Test005.test       2  avgt    3  8.014 ± 114.737  us/op
Test005.test       3  avgt    3  2.876 ±  10.185  us/op
Test005.test       4  avgt    3  4.924 ±  37.390  us/op
```
这里结果列多了一列，type.
## JMH 的测试套件Fixture
### Setup/
会在每一个基准测试方法执行前被调用，通常用于资源的初始化
在基准测试方法被执行之后被调用，通常可用于资源的回收清理工作
#### Level
在默认情况下，Setup和TearDown会在一个基准方法的所有批次执行前后分别执行，
如果需要在每一个批次或者每一次基准方法调用执行的前后执行对应的套件方法，则需要对@Setup和@TearDown进行简单的配置。
- Trial
  - 默认的配置
  - 该套件方法会在每一个基准测试方法的所有批次执行的前后被执行。
```java
@Setup(Level.Trial)
public void setUp()
```
- Iteration
  - 在基准测试的每个批次前后调用，包括预热和度量
```java
@Setup(Level.Iteration)
public void setUp()
```
- Invocation
  - 在每一个批次的度量过程中，每一次对基准方法的调用前后都会执行套件方法。
  - 每一批次有很多次调用方法
```java
@Setup(Level.Invocation)
public void setUp()
```
> [!note]
> 注意的是
> 套件方法的执行也会产生CPU时间的消耗，但是JMH并不会将这部分时间纳入基准方法的统计之中，这一点更进一步地说明了JMH的严谨之处。
## CompilerControl
通过CompilerControl禁止JVM运行时优化和编译
```java
@CompilerControl(CompilerControl.Mode.EXCLUDE)
@Benchmark
public void test(){}
```
- 通过编写程序的方式禁止JVM运行期动态编译和优化
- 在启动JVM时增加参数 -Djava.compiler=NONE。
# 高级
## 编写正确的用例
### 避免DCE
Dead Code Elimination
JVM为我们擦去了一些上下文无关，甚至经过计算之后确定压根不会用到的代码
比如下面这些：
```java
public void test(){
  int x = 10;
  int y = 10;
  int z = x + y;
}
```
既没有对z进行返回，也没有对其进行二次使用，z甚至不是一个全局的变量
JVM很有可能会将test()方法当作一个空的方法来看待，也就是说会擦除对x、y的定义，以及计算z的相关代码
> [!note]
> 通过这个例子我们可以发现，若想要编写性能良好的微基准测试方法，则不要让方法存在Dead Code，最好每一个基准测试方法都有返回值。
### 使用Blackhole
JMH提供了一个称为Blackhole的类，可以在不作任何返回的情况下避免DeadCode的发生，Blackhole直译为“黑洞”，与Linux系统下的黑洞设备/dev/null非常相似
> 假设在基准测试方法中，需要将两个计算结果作为返回值，那么我们该如何去做呢？我们第一时间想到的可能是将结果存放到某个数组或者容器当中作为返回值，但是这种对数组或者容器的操作会对性能统计造成干扰，因为对数组或者容器的写操作也是需要花费一定的CPU时间的。
```java
@Benchmark
public void useBlackhole(Blackhole hole){
  // 将结果存放到black hole中，不会发生擦除，对结果更准确
  hole.consume(Math.pow(1,3));
  hole.consume(Math.pow(2,4));

}
```
### 避免常量折叠
常量折叠是Java编译器早期的一种优化——编译优化。在javac对源文件进行编译的过程中，通过词法分析可以发现某些常量是可以被折叠的，也就是可以直接将计算结果存放到声明中，而不需要在执行阶段再次进行运算
```java
private final int x = 10;
private final int y = x * 20;
```
> 在编译阶段，y的值将被直接赋予200，这就是所谓的常量折叠
所以在测试的时候，要按照实际代码需求编写变量，不能将非常量在测试代码中编写为常量
### Fork用于避免Profile-guided optimizations
默认情况下所有的代码都在一个进程中运行，相同的代码在不同时刻的执行可能会引入前一阶段对进程profiler的优化，甚至会混入其他代码profiler优化时的参数，这很有可能会导致我们所编写的微基准测试出现不准确的问题。
```java
@BenchmarkMode(Mode.AverageTime)
@Fork(0)
@Warmup(iterations = 5)
@Measurement(iterations = 5)
@OutputTimeUnit(TimeUnit.NANOSECONDS)
@State(Scope.Thread)
public class Test006 {
    interface Inc {
        int inc();
    }

    public static class Inc1 implements Inc {
        private int i = 0;

        @Override
        public int inc() {
            return i++;
        }
    }

    public static class Inc2 implements Inc {
        private int i = 0;

        @Override
        public int inc() {
            return i++;
        }
    }

    // 上面两个实现一模一样
    private Inc inc1 = new Inc1();
    private Inc inc2 = new Inc2();

    private int measure(Inc inc) {
        int result = 0;
        for (int i = 0; i < 10; i++) {
            result += inc.inc();
        }
        return result;
    }

    @Benchmark
    public int m_inc_1(){
        return this.measure(inc1);
    }

    @Benchmark
    public int m_inc_2(){
        return this.measure(inc2);
    }

    @Benchmark
    public int m_inc_3(){
        return this.measure(inc1);
    }

    public static void main(String[] args) throws RunnerException {
        Options options = new OptionsBuilder()
                .include(Test006.class.getSimpleName())
                .build();
        new Runner(options).run();
    }

}
```
```bash
如果没有Fork的话，也会有警告
# *** WARNING: Non-forked runs may silently omit JVM options, mess up profilers, disable compiler hints, etc. ***
# *** WARNING: Use non-forked runs only for debugging purposes, not for actual performance runs. ***

Benchmark        Mode  Cnt  Score   Error  Units
Test006.m_inc_1  avgt    5  2.356 ± 0.107  ns/op
Test006.m_inc_2  avgt    5  2.440 ± 0.080  ns/op
Test006.m_inc_3  avgt    5  4.006 ± 0.197  ns/op
```
将Fork设置为1的时候，也就是说每一次运行基准测试时都会开辟一个全新的JVM进程对其进行测试，那么多个基准测试之间将不会再存在干扰。
```java
Test006.m_inc_1  avgt    5  3.057 ± 0.136  ns/op
Test006.m_inc_2  avgt    5  3.219 ± 0.246  ns/op
Test006.m_inc_3  avgt    5  3.082 ± 0.169  ns/op
```
## 部分高级用法
### Asymmetric Benchmark
有些时候我们会想要对某个类的读写方法并行执行，比如，我们想要在修改某个原子变量的时候又有其他线程对其进行读取操作
```java
@GroupThread(5)
@Group("q")
...
```
### Interrupts Benchmark
在测试某些情况下，比如BlockingQueue的时候，put和take任何一个结束太早，都会导致另一个长时间等待阻塞。直到JMH默认的 10 分钟。
所以可以为每个批次设置超时时间
```java
new OptionsBuilder().include(...).timeout(TimeValue.seconds(10)).build();
```
# JMH的Profiler
JMH提供了一些非常有用的Profiler可以帮助我们更加深入地了解基准测试，甚至还能帮助开发者分析所编写的代码
## StackProfiler
不仅可以输出线程堆栈的信息，还能统计程序在执行的过程中线程状态的数据，比如RUNNING状态、WAIT状态所占用的百分比等
```java
@BenchmarkMode(Mode.AverageTime)
@Fork(1)
@Warmup(iterations = 3)
@Measurement(iterations = 3)
@OutputTimeUnit(TimeUnit.MILLISECONDS)
@State(Scope.Thread)
public class Test007 {

    private final static int VALUE = 1;

    @GroupThreads(5)
    @Group("q")
    @Benchmark
    public void put() throws InterruptedException {
        TimeUnit.SECONDS.sleep(VALUE);
    }

    @GroupThreads(5)
    @Group("q")
    @Benchmark
    public void take() throws InterruptedException {
        TimeUnit.SECONDS.sleep(VALUE);
    }

    public static void main(String[] args) throws RunnerException {
        Options options = new OptionsBuilder()
                .include(Test007.class.getSimpleName())
                .timeout(TimeValue.seconds(10))
                .addProfiler(StackProfiler.class)
                .build();

        new Runner(options).run();
    }
}
```
```bash
Result "org.lub.demo001.Test007.q":
  1002.134 ±(99.9%) 11.721 ms/op [Average]
  (min, avg, max) = (1001.413, 1002.134, 1002.646), stdev = 0.642
  CI (99.9%): [990.413, 1013.855] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:put":
  1002.139 ±(99.9%) 12.127 ms/op [Average]
  (min, avg, max) = (1001.391, 1002.139, 1002.663), stdev = 0.665
  CI (99.9%): [990.012, 1014.266] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:take":
  1002.128 ±(99.9%) 11.317 ms/op [Average]
  (min, avg, max) = (1001.434, 1002.128, 1002.629), stdev = 0.620
  CI (99.9%): [990.811, 1013.445] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·stack":
Stack profiler:

-----------------------------------------------------------------------
....[Thread state distributions]....................................................................
 91.4%         TIMED_WAITING
  8.4%         RUNNABLE
  0.2%         WAITING

-----------------------------------------------------------------------

....[Thread state: TIMED_WAITING]...................................................................
 83.1%  90.9% java.lang.Thread.sleep
  8.3%   9.1% java.lang.Object.wait

....[Thread state: RUNNABLE]........................................................................
  8.3%  99.4% java.net.SocketInputStream.socketRead0
  0.0%   0.2% jdk.internal.misc.Unsafe.getAndAddInt
  0.0%   0.1% java.lang.System.nanoTime
  0.0%   0.1% jdk.internal.misc.Unsafe.getIntVolatile
  0.0%   0.0% java.lang.Thread.sleep
  0.0%   0.0% java.lang.invoke.VarHandleGuards.guard_LLL_Z
  0.0%   0.0% java.lang.Thread.currentThread
  0.0%   0.0% java.lang.reflect.AccessibleObject.verifyAccess
  0.0%   0.0% org.openjdk.jmh.runner.BenchmarkHandler.newWorkerData

....[Thread state: WAITING].........................................................................
  0.2% 100.0% jdk.internal.misc.Unsafe.park

# Run complete. Total time: 00:01:12

REMEMBER: The numbers below are just data. To gain reusable insights, you need to follow up on
why the numbers are the way they are. Use profilers (see -prof, -lprof), design factorial
experiments, perform baseline and negative tests that provide experimental control, make sure
the benchmarking environment is safe on JVM/OS/HW level, ask for reviews from the domain experts.
Do not assume the numbers tell you what you want them to tell.

Benchmark         Mode  Cnt     Score    Error  Units
Test007.q         avgt    3  1002.134 ± 11.721  ms/op
Test007.q:put     avgt    3  1002.139 ± 12.127  ms/op
Test007.q:take    avgt    3  1002.128 ± 11.317  ms/op
Test007.q:·stack  avgt            NaN             ---
```
## GcProfiler
可用于分析出在测试方法中垃圾回收器在JVM每个内存空间上所花费的时间
```java
public static void main(String[] args) throws RunnerException {
    Options options = new OptionsBuilder()
            .include(Test007.class.getSimpleName())
            .timeout(TimeValue.seconds(10))
            .addProfiler(GCProfiler.class)
            .jvmArgsAppend("-Xmx18M")
            .build();

    new Runner(options).run();
}
```
```bash
Result "org.lub.demo001.Test007.q":
  1002.650 ±(99.9%) 4.971 ms/op [Average]
  (min, avg, max) = (1002.491, 1002.650, 1002.965), stdev = 0.272
  CI (99.9%): [997.679, 1007.621] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:put":
  1002.652 ±(99.9%) 5.242 ms/op [Average]
  (min, avg, max) = (1002.482, 1002.652, 1002.984), stdev = 0.287
  CI (99.9%): [997.410, 1007.895] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:take":
  1002.648 ±(99.9%) 4.700 ms/op [Average]
  (min, avg, max) = (1002.497, 1002.648, 1002.945), stdev = 0.258
  CI (99.9%): [997.947, 1007.348] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·gc.alloc.rate":
  0.001 ±(99.9%) 0.001 MB/sec [Average]
  (min, avg, max) = (0.001, 0.001, 0.001), stdev = 0.001
  CI (99.9%): [0.001, 0.001] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·gc.alloc.rate.norm":
  142.560 ±(99.9%) 15.446 B/op [Average]
  (min, avg, max) = (141.600, 142.560, 143.200), stdev = 0.847
  CI (99.9%): [127.114, 158.006] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·gc.count":
  ≈ 0 counts

# Run complete. Total time: 00:01:15

Benchmark                      Mode  Cnt     Score    Error   Units
Test007.q                      avgt    3  1002.650 ±  4.971   ms/op
Test007.q:put                  avgt    3  1002.652 ±  5.242   ms/op
Test007.q:take                 avgt    3  1002.648 ±  4.700   ms/op
Test007.q:·gc.alloc.rate       avgt    3     0.001 ±  0.001  MB/sec
Test007.q:·gc.alloc.rate.norm  avgt    3   142.560 ± 15.446    B/op
Test007.q:·gc.count            avgt    3       ≈ 0           counts
```
## ClassLoaderProfiler
可以帮助我们看到在基准方法的执行过程中有多少类被加载和卸载，但是考虑到在一个类加载器中同一个类只会被加载一次的情况，
因此我们需要将Warmup设置为0，以避免在热身阶段就已经加载了基准测试方法所需的所有类。
```java
public static void main(String[] args) throws RunnerException {
    Options options = new OptionsBuilder()
            .include(Test007.class.getSimpleName())
            .timeout(TimeValue.seconds(10))
            .addProfiler(ClassloaderProfiler.class)
            .build();

    new Runner(options).run();
}
```
```bash
Result "org.lub.demo001.Test007.q":
  1002.108 ±(99.9%) 0.493 ms/op [Average]
  (min, avg, max) = (1002.090, 1002.108, 1002.139), stdev = 0.027
  CI (99.9%): [1001.616, 1002.601] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:put":
  1002.103 ±(99.9%) 0.647 ms/op [Average]
  (min, avg, max) = (1002.077, 1002.103, 1002.144), stdev = 0.035
  CI (99.9%): [1001.456, 1002.751] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:take":
  1002.113 ±(99.9%) 0.408 ms/op [Average]
  (min, avg, max) = (1002.090, 1002.113, 1002.135), stdev = 0.022
  CI (99.9%): [1001.705, 1002.521] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·class.load":
  84.487 ±(99.9%) 2511.411 classes/sec [Average]
  (min, avg, max) = (≈ 0, 84.487, 243.334), stdev = 137.659
  CI (99.9%): [≈ 0, 2595.898] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·class.load.norm":
  0.083 ±(99.9%) 2.477 classes/op [Average]
  (min, avg, max) = (≈ 0, 0.083, 0.240), stdev = 0.136
  CI (99.9%): [≈ 0, 2.560] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·class.unload":
  ≈ 0 classes/sec

Secondary result "org.lub.demo001.Test007.q:·class.unload.norm":
  ≈ 0 classes/op

# Run complete. Total time: 00:00:41

Benchmark                     Mode  Cnt     Score      Error        Units
Test007.q                     avgt    3  1002.108 ±    0.493        ms/op
Test007.q:put                 avgt    3  1002.103 ±    0.647        ms/op
Test007.q:take                avgt    3  1002.113 ±    0.408        ms/op
Test007.q:·class.load         avgt    3    84.487 ± 2511.411  classes/sec
Test007.q:·class.load.norm    avgt    3     0.083 ±    2.477   classes/op
Test007.q:·class.unload       avgt    3       ≈ 0             classes/sec
Test007.q:·class.unload.norm  avgt    3       ≈ 0              classes/op
```
## CompilerProfiler
将会告诉你在代码的执行过程中JIT编译器所花费的优化时间
可以打开verbose模式观察更详细的输出。
```java
public static void main(String[] args) throws RunnerException {
    Options options = new OptionsBuilder()
            .include(Test007.class.getSimpleName())
            .timeout(TimeValue.seconds(10))
            .addProfiler(CompilerProfiler.class)
            .verbosity(VerboseMode.EXTRA)
            .build();

    new Runner(options).run();
}
```
```bash
Result "org.lub.demo001.Test007.q":
  1002.870 ±(99.9%) 1.891 ms/op [Average]
  (min, avg, max) = (1002.316, 1002.870, 1003.460), stdev = 0.491
  CI (99.9%): [1000.978, 1004.761] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:put":
  1002.867 ±(99.9%) 1.877 ms/op [Average]
  (min, avg, max) = (1002.337, 1002.867, 1003.474), stdev = 0.488
  CI (99.9%): [1000.990, 1004.745] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:take":
  1002.872 ±(99.9%) 1.908 ms/op [Average]
  (min, avg, max) = (1002.296, 1002.872, 1003.447), stdev = 0.496
  CI (99.9%): [1000.964, 1004.780] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·compiler.time.profiled":
  17.000 ±(99.9%) 0.001 ms [Sum]
  (min, avg, max) = (≈ 0, 3.400, 6.000), stdev = 2.408
  CI (99.9%): [17.000, 17.000] (assumes normal distribution)

Secondary result "org.lub.demo001.Test007.q:·compiler.time.total":
  356.000 ±(99.9%) 0.001 ms [Maximum]
  (min, avg, max) = (341.000, 348.400, 356.000), stdev = 5.941
  CI (99.9%): [356.000, 356.000] (assumes normal distribution)

# Run complete. Total time: 00:01:31

Benchmark                          Mode  Cnt     Score   Error  Units
Test007.q                          avgt    5  1002.870 ± 1.891  ms/op
Test007.q:put                      avgt    5  1002.867 ± 1.877  ms/op
Test007.q:take                     avgt    5  1002.872 ± 1.908  ms/op
Test007.q:·compiler.time.profiled  avgt    5    17.000             ms
Test007.q:·compiler.time.total     avgt    5   356.000             ms
```

## 最佳实践

- **JMH 只用于微基准**：方法级性能对比（集合/算法/锁），宏观性能用压测工具
- **正确性优先**：Blackhole 消费结果防 DCE，Fork 防 profile-guided 优化
- **预热必须充分**：warmup 让 JIT 完成编译，measurement 才反映真实
- **结果看相对值**：同环境对比才有意义，绝对值受机器影响

## 常见踩坑

| 编号 | 坑 | 现象 | 解决方案 |
|---|---|---|---|
| #J1 | 结果没被消费 | 编译器消除代码（DCE） | Blackhole 接收结果 |
| #J2 | 常量折叠 | 结果被编译器预计算 | 参数用 @State 运行时变量 |
| #J3 | 预热不足 | 首轮测量含 JIT 编译开销 | warmupIterations 调大 |
| #J4 | 忽略 Fork | profile-guided 优化干扰 | forks 设为 2+ |
| #J5 | 微基准测宏观场景 | 结果误导 | 宏观用压测工具 |

## 小结

- JMH 是 Oracle 官方微基准工具，对抗 JIT 优化
- 核心注解：@Benchmark/@State/@Param/@Setup/@BenchmarkMode
- 正确性三坑：DCE/常量折叠/profile-guided 优化 → Blackhole/Fork 解决
- Profiler：Stack/Gc/ClassLoader/Compiler 四类分析

## 下一篇

[04-AssertJ与断言最佳实践](04-AssertJ与断言最佳实践.md)——让测试断言更可读

## 参考资料

- [JMH 官方 GitHub](https://github.com/openjdk/jmh)，查询日期：2026-08-09
- [JMH 官方样例](https://github.com/openjdk/jmh/tree/master/jmh-samples)，查询日期：2026-08-09
