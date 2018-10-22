import com.github.javaparser.JavaParser;
import com.github.javaparser.JavaToken;
import com.github.javaparser.ast.CompilationUnit;
import com.github.javaparser.ast.body.MethodDeclaration;
import com.github.javaparser.ast.expr.MethodCallExpr;
import com.github.javaparser.ast.expr.ObjectCreationExpr;
import com.github.javaparser.ast.visitor.VoidVisitorAdapter;
import org.apache.commons.lang3.StringUtils;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.StreamSupport;

public class Main {

    public static void main(String[] args) {
        String nameFile = "names.txt";
        String apiFile = "api.txt";
        String tokenFile = "tokens.txt";
        String commentFile = "comments.txt";

        try (Writer names = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(nameFile), StandardCharsets.UTF_8));
             Writer apiCalls = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(apiFile), StandardCharsets.UTF_8));
             Writer tokens = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(tokenFile), StandardCharsets.UTF_8));
             Writer comments = new BufferedWriter(new OutputStreamWriter(new FileOutputStream(commentFile), StandardCharsets.UTF_8));
             FileInputStream in = new FileInputStream("Test.java")) {

            CompilationUnit cu = JavaParser.parse(in);

            for (MethodDeclaration method : cu.findAll(MethodDeclaration.class)) {
                // write the method name
                String methodName = method.getNameAsString();
                List<String> nameList = Arrays.asList(StringUtils.splitByCharacterTypeCamelCase(methodName));
                names.write(String.join(" ", nameList).toLowerCase());
                names.write("\n");

                // Write javadoc comment
                if (method.getJavadoc().isPresent()) {
                    String firstLine = method.getJavadoc().get().getDescription().toText().split("\\r?\\n")[0];
                    comments.write(firstLine.toLowerCase());
                    comments.write("\n");
                } else {
                    comments.write("\n");
                }

                // Body
                if (method.getBody().isPresent()) {
                    // tokenize
                    // only filter for kind=89 -> identifier
                    if (method.getBody().get().getTokenRange().isPresent()) {
                        Set<String> bodyTokens = new HashSet<>();
                        StreamSupport.<JavaToken>stream(method.getBody().get().getTokenRange().get().spliterator(), false)
                                .filter(token -> token.getKind() == 89)
                                .forEach(t -> bodyTokens.addAll(Arrays.asList(StringUtils.splitByCharacterTypeCamelCase(t.asString()))));

                        tokens.write(String.join(" ", bodyTokens).toLowerCase());
                        tokens.write("\n");
                    } else {
                        tokens.write("\n");
                    }

                    // Sequence api calls
                    List<String> sequenceAPI = new ArrayList<>();
                    // BlockStmnt
                    method.getBody().get().accept(new APICallsVisitor(), sequenceAPI);
                    apiCalls.write(String.join(" ", sequenceAPI));
                    apiCalls.write("\n");
                } else {
                    tokens.write("\n");
                    apiCalls.write("\n");
                }
            }
        } catch (IOException e) {
            System.out.println("Error");
        }
    }
    
    private static void forEachJavaFile(File directory) {
        // TODO: walk through all files and directories searching for .java files

    }

    private static class APICallsVisitor extends VoidVisitorAdapter<List<String>> {
        @Override
        public void visit(MethodCallExpr n, List<String> arg) {
            n.getArguments().forEach(p -> p.accept(this, arg));
            n.getScope().ifPresent(l -> l.accept(this, arg));
            n.getName().accept(this, arg);
            n.getTypeArguments().ifPresent(l -> l.forEach(v -> v.accept(this, arg)));
            n.getComment().ifPresent(l -> l.accept(this, arg));

            arg.add(n.getName().asString());
        }

        @Override
        public void visit(ObjectCreationExpr n, List<String> arg) {
            // TODO: do we need this?
            //arg.add(n.getType().asString());
            super.visit(n, arg);
        }
    }
}
