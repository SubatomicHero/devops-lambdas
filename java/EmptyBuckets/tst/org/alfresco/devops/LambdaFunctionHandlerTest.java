package org.alfresco.devops;

import static org.junit.Assert.assertEquals;

import java.io.IOException;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mockito;
import org.powermock.api.mockito.PowerMockito;
import org.powermock.core.classloader.annotations.PowerMockIgnore;
import org.powermock.core.classloader.annotations.PrepareForTest;
import org.powermock.modules.junit4.PowerMockRunner;

import com.amazonaws.SdkClientException;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.model.ListVersionsRequest;
import com.amazonaws.services.s3.model.S3VersionSummary;
import com.amazonaws.services.s3.model.VersionListing;

/**
 * A simple test harness for locally invoking your Lambda function handler.
 */
/**
 * @author mmancuso
 *
 */

@RunWith(PowerMockRunner.class)
@PowerMockIgnore({"org.apache.http.*","javax.management.*","org.apache.http.conn.ssl.*", "javax.net.ssl.*" , "javax.crypto.*"})
@PrepareForTest(EmptyBucktetsLambdaFunctionHandler.class )
public class LambdaFunctionHandlerTest {

	private static Map<String, Object> input;

	@Before
	public void createInput() throws IOException {
		// TODO: set up your sample input object here.
		input = new HashMap<String,Object>();
		Map<String, Object> input2 = new HashMap<String,Object>();
		input.put("RequestType", "Delete");
		input.put("ServiceToken", "arn:aws:lambda:us-east-1:632333955013:function:emptyBucketLambdaJava");
		input.put("ResponseURL", "https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/arn%3Aaws%3Acloudformation%3Aus-east-1%3A632333955013%3Astack/redd-683-data/459ec080-d338-11e6-9b87-500c217b48d2%7CEmptyBuckets%7Cb7129e31-95b2-4ae8-9b58-6453e58389f1?AWSAccessKeyId=AKIAJNXHFR7P7YGKLDPQ&Expires=1483981902&Signature=Wqw88L6ra6FbzuSFvOLCwEYKz6M%3D");
		input.put("StackId", "arn:aws:cloudformation:us-east-1:632333955013:stack/redd-683-data/459ec080-d338-11e6-9b87-500c217b48d2");
		input.put("RequestId", "afd8d7c5-9376-4013-8b3b-307517b8719e");
		input.put("LogicalResourceId", "EmptyBuckets");
		input.put("ResourceType", "Custom::LambdaDependency");
		input2.put("BucketName", "backup-redd-bamboo-redd-711-1-alf-data");
		input2.put("ServiceToken", "arn:aws:lambda:us-east-1:632333955013:function:emptyBucketLambda");
		input.put("ResourceProperties", input2);   
	}

	private Context createContext() {
		TestContext ctx = new TestContext();

		ctx.setFunctionName("Your Function Name");

		return ctx;
	}

	/**
	 * When bucket exist and request is to Delete it returns SUCCESS
	 */
	@Test
	public void testLambdaFunctionHandler() {

		@SuppressWarnings("unchecked")
		Map<String,Object> resourceProps = (Map<String,Object>)input.get("ResourceProperties");
		String bucketName = (String) resourceProps.get("BucketName");

		EmptyBucktetsLambdaFunctionHandler handler = new EmptyBucktetsLambdaFunctionHandler();
		Context ctx = createContext();
		URL mockURL = PowerMockito.mock(URL.class);
		URLConnection mockConn=PowerMockito.mock(HttpURLConnection.class);
		OutputStream osMock = PowerMockito.mock(OutputStream.class);
		AmazonS3Client ascMock = PowerMockito.mock(AmazonS3Client.class);
		VersionListing vlMock = PowerMockito.mock(VersionListing.class);
		S3VersionSummary s3vsumMock = PowerMockito.mock(S3VersionSummary.class);
		List<S3VersionSummary> summaryList = Arrays.asList(s3vsumMock, s3vsumMock, s3vsumMock);
		ListVersionsRequest lvrMock = PowerMockito.mock(ListVersionsRequest.class);

		try {

			PowerMockito.whenNew(URL.class).withArguments(input.get("ResponseURL")).thenReturn(mockURL);
			PowerMockito.whenNew(AmazonS3Client.class).withNoArguments().thenReturn(ascMock);
			PowerMockito.whenNew(ListVersionsRequest.class).withNoArguments().thenReturn(lvrMock);

			Mockito.when(mockURL.openConnection()).thenReturn(mockConn);
			Mockito.when(mockConn.getOutputStream()).thenReturn(osMock);
			Mockito.when(ascMock.doesBucketExist(bucketName)).thenReturn(true);
			Mockito.when(lvrMock.withBucketName(bucketName)).thenReturn(lvrMock);			
			Mockito.when(ascMock.listVersions(lvrMock)).thenReturn(vlMock);
			Mockito.when(vlMock.getVersionSummaries()).thenReturn(summaryList);
			Mockito.when(vlMock.isTruncated()).thenReturn(false);
			Mockito.when(ascMock.listNextBatchOfVersions(vlMock)).thenReturn(vlMock);

			String result = (String)handler.handleRequest(input, ctx);

			Mockito.verify(ascMock, Mockito.times(1)).deleteBucket(bucketName);
			Mockito.verify(ascMock, Mockito.times(summaryList.size())).deleteVersion(Mockito.anyString(),Mockito.anyString(),Mockito.anyString());

			assertEquals(result,"SUCCESS");

		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	/**
	 * When bucket does not exist it returns SUCCESS
	 */
	@Test
	public void testLambdaFunctionHandler2() {

		@SuppressWarnings("unchecked")
		Map<String,Object> resourceProps = (Map<String,Object>)input.get("ResourceProperties");
		String bucketName = (String) resourceProps.get("BucketName");

		EmptyBucktetsLambdaFunctionHandler handler = new EmptyBucktetsLambdaFunctionHandler();
		Context ctx = createContext();
		URL mockURL = PowerMockito.mock(URL.class);
		URLConnection mockConn=PowerMockito.mock(HttpURLConnection.class);
		OutputStream osMock = PowerMockito.mock(OutputStream.class);
		AmazonS3Client ascMock = PowerMockito.mock(AmazonS3Client.class);
		VersionListing vlMock = PowerMockito.mock(VersionListing.class);
		S3VersionSummary s3vsumMock = PowerMockito.mock(S3VersionSummary.class);
		List<S3VersionSummary> summaryList = Arrays.asList(s3vsumMock, s3vsumMock, s3vsumMock);
		ListVersionsRequest lvrMock = PowerMockito.mock(ListVersionsRequest.class);

		try {

			PowerMockito.whenNew(URL.class).withArguments(input.get("ResponseURL")).thenReturn(mockURL);
			PowerMockito.whenNew(AmazonS3Client.class).withNoArguments().thenReturn(ascMock);
			PowerMockito.whenNew(ListVersionsRequest.class).withNoArguments().thenReturn(lvrMock);

			Mockito.when(mockURL.openConnection()).thenReturn(mockConn);
			Mockito.when(mockConn.getOutputStream()).thenReturn(osMock);
			Mockito.when(ascMock.doesBucketExist(bucketName)).thenReturn(false);
			Mockito.when(lvrMock.withBucketName(bucketName)).thenReturn(lvrMock);			
			Mockito.when(ascMock.listVersions(lvrMock)).thenReturn(vlMock);
			Mockito.when(vlMock.getVersionSummaries()).thenReturn(summaryList);
			Mockito.when(vlMock.isTruncated()).thenReturn(false);
			Mockito.when(ascMock.listNextBatchOfVersions(vlMock)).thenReturn(vlMock);

			String result = (String)handler.handleRequest(input, ctx);

			Mockito.verify(ascMock, Mockito.never()).deleteBucket(bucketName);
			Mockito.verify(ascMock, Mockito.never()).deleteVersion(Mockito.anyString(),Mockito.anyString(),Mockito.anyString());

			assertEquals(result,"SUCCESS");

		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	/**
	 * When requestType is CREATE it returns SUCCESS
	 */
	@Test
	public void testLambdaFunctionHandler3() {

		input.put("RequestType", "Create");

		@SuppressWarnings("unchecked")
		Map<String,Object> resourceProps = (Map<String,Object>)input.get("ResourceProperties");
		String bucketName = (String) resourceProps.get("BucketName");

		EmptyBucktetsLambdaFunctionHandler handler = new EmptyBucktetsLambdaFunctionHandler();
		Context ctx = createContext();
		URL mockURL = PowerMockito.mock(URL.class);
		URLConnection mockConn=PowerMockito.mock(HttpURLConnection.class);
		OutputStream osMock = PowerMockito.mock(OutputStream.class);
		AmazonS3Client ascMock = PowerMockito.mock(AmazonS3Client.class);
		VersionListing vlMock = PowerMockito.mock(VersionListing.class);
		S3VersionSummary s3vsumMock = PowerMockito.mock(S3VersionSummary.class);
		List<S3VersionSummary> summaryList = Arrays.asList(s3vsumMock, s3vsumMock, s3vsumMock);
		ListVersionsRequest lvrMock = PowerMockito.mock(ListVersionsRequest.class);

		try {

			PowerMockito.whenNew(URL.class).withArguments(input.get("ResponseURL")).thenReturn(mockURL);
			PowerMockito.whenNew(AmazonS3Client.class).withNoArguments().thenReturn(ascMock);
			PowerMockito.whenNew(ListVersionsRequest.class).withNoArguments().thenReturn(lvrMock);

			Mockito.when(mockURL.openConnection()).thenReturn(mockConn);
			Mockito.when(mockConn.getOutputStream()).thenReturn(osMock);
			Mockito.when(ascMock.doesBucketExist(bucketName)).thenReturn(true);
			Mockito.when(lvrMock.withBucketName(bucketName)).thenReturn(lvrMock);			
			Mockito.when(ascMock.listVersions(lvrMock)).thenReturn(vlMock);
			Mockito.when(vlMock.getVersionSummaries()).thenReturn(summaryList);
			Mockito.when(vlMock.isTruncated()).thenReturn(false);
			Mockito.when(ascMock.listNextBatchOfVersions(vlMock)).thenReturn(vlMock);

			String result = (String)handler.handleRequest(input, ctx);

			Mockito.verify(ascMock, Mockito.never()).deleteBucket(bucketName);
			Mockito.verify(ascMock, Mockito.never()).deleteVersion(Mockito.anyString(),Mockito.anyString(),Mockito.anyString());

			assertEquals(result,"SUCCESS");

		} catch (Exception e) {
			e.printStackTrace();
		}
	}
	
	/**
	 * When an exception is thrown than it returns FAILED
	 */
	@Test
	public void testLambdaFunctionHandler4() {

		@SuppressWarnings("unchecked")
		Map<String,Object> resourceProps = (Map<String,Object>)input.get("ResourceProperties");
		String bucketName = (String) resourceProps.get("BucketName");

		EmptyBucktetsLambdaFunctionHandler handler = new EmptyBucktetsLambdaFunctionHandler();
		Context ctx = createContext();
		URL mockURL = PowerMockito.mock(URL.class);
		URLConnection mockConn=PowerMockito.mock(HttpURLConnection.class);
		OutputStream osMock = PowerMockito.mock(OutputStream.class);
		AmazonS3Client ascMock = PowerMockito.mock(AmazonS3Client.class);
		VersionListing vlMock = PowerMockito.mock(VersionListing.class);
		S3VersionSummary s3vsumMock = PowerMockito.mock(S3VersionSummary.class);
		List<S3VersionSummary> summaryList = Arrays.asList(s3vsumMock, s3vsumMock, s3vsumMock);
		ListVersionsRequest lvrMock = PowerMockito.mock(ListVersionsRequest.class);

		try {

			PowerMockito.whenNew(URL.class).withArguments(input.get("ResponseURL")).thenReturn(mockURL);
			PowerMockito.whenNew(AmazonS3Client.class).withNoArguments().thenReturn(ascMock);
			PowerMockito.whenNew(ListVersionsRequest.class).withNoArguments().thenReturn(lvrMock);

			Mockito.when(mockURL.openConnection()).thenReturn(mockConn);
			Mockito.when(mockConn.getOutputStream()).thenReturn(osMock);
			
			Mockito.when(ascMock.doesBucketExist(bucketName)).thenThrow(new SdkClientException("an exception"));

			
			Mockito.when(lvrMock.withBucketName(bucketName)).thenReturn(lvrMock);			
			Mockito.when(ascMock.listVersions(lvrMock)).thenReturn(vlMock);
			Mockito.when(vlMock.getVersionSummaries()).thenReturn(summaryList);
			Mockito.when(vlMock.isTruncated()).thenReturn(false);
			Mockito.when(ascMock.listNextBatchOfVersions(vlMock)).thenReturn(vlMock);

			String result = (String)handler.handleRequest(input, ctx);

			Mockito.verify(ascMock, Mockito.never()).deleteBucket(bucketName);
			Mockito.verify(ascMock, Mockito.never()).deleteVersion(Mockito.anyString(),Mockito.anyString(),Mockito.anyString());

			assertEquals(result,"FAILED");

		} catch (Exception e) {
			e.printStackTrace();
		}
	}
}
