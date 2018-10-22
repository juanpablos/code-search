/**
 * This is documentation
 */
public class Test {
    /**
     * Variable decumentation
     */
    private int variable = 10;

    public Test(int variable) {
        this.variable = variable;
    }

    /**
     * More documentation
     *
     * A detailed explanation
     *
     * @param some parameter
     * @param parameters some parameters
     * @return the length
     */
    public int method1(int some, String parameters) {
        String a = new String("hello hello");
        a.equals("qwe");
        return parameters.length().hola().chao().aaaa();
    }

    /**
     * More documentation
     */
    public int method2() {
        while (new String().size()) {
            continue;
        }
        return 10;
    }


    public void method3() {
        try {
            new ArrayList();
        } catch (Exception e) {
            new ArrayList();
        } finally {
            new ArrayList();
        }
    }

    public void method4() {
        new ArrayList().stream().foreach(() -> System.out.println("HOLA"));
    }
}
